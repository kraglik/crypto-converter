import asyncio
import time
from enum import Enum
from typing import Any, Optional, Union

import aiohttp
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from converter.adapters.outbound.external.binance.models import (
    BinanceExchangeInfo,
    BinanceServerTime,
    BinanceTicker,
)
from converter.domain.exceptions.quote_provider import QuoteProviderUnavailableError
from converter.shared.logging import get_logger

logger = get_logger(__name__)


class BinanceEndpoint(str, Enum):
    TIME = "/api/v3/time"
    TICKER_PRICE = "/api/v3/ticker/price"
    EXCHANGE_INFO = "/api/v3/exchangeInfo"


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("circuit_breaker_half_open", attempting_reset=True)
                else:
                    raise QuoteProviderUnavailableError(
                        "Binance",
                        f"Circuit breaker is open. Waiting for recovery timeout.",
                    )

            current_state = self.state

        try:
            result = await func(*args, **kwargs)

            if current_state == CircuitBreakerState.HALF_OPEN:
                await self._on_success()

            return result

        except self.expected_exception:
            await self._on_failure()
            raise

    async def _on_success(self):
        async with self._lock:
            self.failure_count = 0
            self.state = CircuitBreakerState.CLOSED
            logger.info("circuit_breaker_closed", failure_count_reset=True)

    async def _on_failure(self):
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold,
                )

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time
            and (time.time() - self.last_failure_time) >= self.recovery_timeout
        )


class BinanceAPIClient:
    BASE_URL = "https://api.binance.com"

    def __init__(
        self,
        timeout: int = 10,
        max_connections: int = 10,
        max_connections_per_host: int = 5,
        enable_circuit_breaker: bool = True,
        circuit_breaker_failure_threshold: int = 5,
        circuit_breaker_recovery_timeout: int = 60,
    ):
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._max_connections = max_connections
        self._max_connections_per_host = max_connections_per_host
        self._session: Optional[aiohttp.ClientSession] = None

        self._circuit_breaker: Optional[CircuitBreaker] = None
        if enable_circuit_breaker:
            self._circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_failure_threshold,
                recovery_timeout=circuit_breaker_recovery_timeout,
                expected_exception=QuoteProviderUnavailableError,
            )

    async def __aenter__(self) -> "BinanceAPIClient":
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            await asyncio.sleep(0.25)
            self._session = None
            logger.debug("binance_client_closed")

    async def get_server_time(self) -> BinanceServerTime:
        """
        Get Binance server time.

        :return: BinanceServerTime object
        :raises QuoteProviderUnavailableError: If request fails
        """
        if self._circuit_breaker:
            data = await self._circuit_breaker.call(
                self._api_call, endpoint=BinanceEndpoint.TIME, description="server time"
            )
        else:
            data = await self._api_call(
                endpoint=BinanceEndpoint.TIME, description="server time"
            )

        try:
            return BinanceServerTime.from_json(data)
        except ValueError as e:
            raise QuoteProviderUnavailableError(
                "Binance", f"Invalid server time response: {e}"
            ) from e

    async def get_all_ticker_prices(self) -> list[BinanceTicker]:
        """
        Get ticker prices for all symbols.

        :return: List of BinanceTicker instances
        :raises QuoteProviderUnavailableError: If request fails
        """
        if self._circuit_breaker:
            data = await self._circuit_breaker.call(
                self._api_call,
                endpoint=BinanceEndpoint.TICKER_PRICE,
                description="all ticker prices",
            )
        else:
            data = await self._api_call(
                endpoint=BinanceEndpoint.TICKER_PRICE, description="all ticker prices"
            )

        if not isinstance(data, list):
            raise QuoteProviderUnavailableError(
                "Binance", f"Expected list response, got {type(data).__name__}"
            )

        try:
            tickers = BinanceTicker.from_json_list(data)
            logger.debug("binance_tickers_fetched", ticker_count=len(tickers))
            return tickers
        except ValueError as e:
            raise QuoteProviderUnavailableError(
                "Binance", f"Invalid ticker response: {e}"
            ) from e

    async def get_exchange_info(self) -> BinanceExchangeInfo:
        """
        Get exchange trading rules and symbol information.

        :return: BinanceExchangeInfo with all symbols
        :raises QuoteProviderUnavailableError: If request fails
        """
        if self._circuit_breaker:
            data = await self._circuit_breaker.call(
                self._api_call,
                endpoint=BinanceEndpoint.EXCHANGE_INFO,
                description="exchange info",
            )
        else:
            data = await self._api_call(
                endpoint=BinanceEndpoint.EXCHANGE_INFO, description="exchange info"
            )

        try:
            exchange_info = BinanceExchangeInfo.from_json(data)
            logger.debug(
                "binance_exchange_info_fetched", symbol_count=len(exchange_info.symbols)
            )
            return exchange_info
        except ValueError as e:
            raise QuoteProviderUnavailableError(
                "Binance", f"Invalid exchange info response: {e}"
            ) from e

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=self._max_connections,
                limit_per_host=self._max_connections_per_host,
                ttl_dns_cache=300,
                enable_cleanup_closed=True,
            )

            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self._timeout,
                headers={
                    "Accept": "application/json",
                },
            )

            logger.debug(
                "binance_session_created",
                max_connections=self._max_connections,
                max_per_host=self._max_connections_per_host,
            )

        return self._session

    async def _api_call(
        self,
        endpoint: BinanceEndpoint,
        params: Optional[dict[str, Any]] = None,
        description: str = "API call",
    ) -> Union[dict[str, Any], list[dict[str, Any]]]:
        """
        Make HTTP GET request to Binance API with automatic retry logic.

        :param endpoint: API endpoint to call
        :param params: Optional query parameters
        :param description: Description for error messages

        :return: Parsed JSON response (dict or list)
        :raises QuoteProviderUnavailableError: If request fails after retries
        """
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=10),
                retry=retry_if_exception_type(
                    (aiohttp.ClientError, asyncio.TimeoutError)
                ),
                reraise=True,
            ):
                with attempt:
                    result = await self._make_request(endpoint, params, description)
                    return result

            # To let linter know we're guaranteed to raise an exception by this point
            raise QuoteProviderUnavailableError(
                "Binance",
                f"{description} failed after retries",
            )

        except RetryError as e:
            original_error = e.last_attempt.exception()
            raise QuoteProviderUnavailableError(
                "Binance",
                f"{description} failed after retries: {original_error}",
            ) from original_error

    async def _make_request(
        self,
        endpoint: BinanceEndpoint,
        params: Optional[dict[str, Any]],
        description: str,
    ) -> Union[dict[str, Any], list[dict[str, Any]]]:

        session = await self._ensure_session()
        url = f"{self.BASE_URL}{endpoint.value}"

        async with session.get(url, params=params) as response:
            logger.debug(
                "binance_api_call",
                endpoint=endpoint.value,
                status=response.status,
            )

            if response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(
                    "binance_rate_limited",
                    endpoint=endpoint.value,
                    retry_after=retry_after,
                )
                await asyncio.sleep(retry_after)

                raise aiohttp.ClientError(f"Rate limited, retry after {retry_after}s")

            if response.status != 200:
                error_text = await response.text()
                raise QuoteProviderUnavailableError(
                    "Binance",
                    f"{description} failed: HTTP {response.status} - {error_text}",
                )

            try:
                data = await response.json()
            except aiohttp.ContentTypeError as e:
                raise QuoteProviderUnavailableError(
                    "Binance", f"{description} returned non-JSON response"
                ) from e

            return data
