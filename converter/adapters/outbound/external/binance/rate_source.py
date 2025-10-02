import asyncio
import time
from typing import AsyncIterator, Optional

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from converter.adapters.outbound.rate_source import RateBatch, RateSource
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.values import Currency, Pair, TimestampUTC
from converter.shared.config import get_settings
from converter.shared.logging import get_logger
from converter.shared.observability import get_metrics_registry
from converter.shared.utils.scheduler import FixedRateScheduler

from .client import BinanceAPIClient
from .mapper import BinanceMapper

logger = get_logger(__name__)
settings = get_settings()


class BinanceStreamingRateSource(RateSource):
    def __init__(
        self,
        api_client: BinanceAPIClient,
        rate_factory: RateFactory,
        rates_interval_seconds: int = 30,
        symbols_interval_seconds: int = 60,
        queue_maxsize: int = 10,
        scheduler: Optional[FixedRateScheduler] = None,
    ) -> None:
        self._client = api_client
        self._mapper = BinanceMapper(rate_factory=rate_factory)

        self._rates_interval = rates_interval_seconds
        self._symbols_interval = symbols_interval_seconds

        self._queue: asyncio.Queue[RateBatch] = asyncio.Queue(maxsize=queue_maxsize)
        self._tracked_pairs: list[Pair] = []

        self._scheduler = scheduler or FixedRateScheduler()
        self._scheduler_task: Optional[asyncio.Task] = None
        self._shutdown = asyncio.Event()
        self._started = False
        self._start_lock = asyncio.Lock()

    async def stream(self) -> AsyncIterator[RateBatch]:
        async with self._start_lock:
            if self._started:
                raise RuntimeError("stream() already started")

            try:
                logger.info("binance_rate_source_initializing")
                await self._init_symbols()
                self._started = True

            except Exception as e:
                logger.error(
                    "binance_rate_source_init_failed", error=str(e), exc_info=True
                )
                self._started = False
                raise

        self._scheduler.schedule(
            self._rates_tick, int(self._rates_interval), "binance_rates_tick"
        )
        self._scheduler.schedule(
            self._symbols_tick, int(self._symbols_interval), "binance_symbols_tick"
        )

        self._scheduler_task = asyncio.create_task(
            self._scheduler.run_until_shutdown(), name="binance_scheduler"
        )

        logger.info(
            "binance_rate_source_streaming",
            rates_interval_seconds=self._rates_interval,
            symbols_interval_seconds=self._symbols_interval,
        )

        try:
            while not self._shutdown.is_set():
                try:
                    batch = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                    yield batch
                except asyncio.TimeoutError:
                    continue

        except asyncio.CancelledError:
            logger.info("binance_stream_cancelled")
            raise
        finally:
            await self.close()

    async def close(self) -> None:
        if self._shutdown.is_set():
            return

        logger.info("binance_rate_source_closing")
        self._shutdown.set()

        try:
            await self._scheduler.shutdown()
        except Exception as e:
            logger.warning("scheduler_shutdown_error", error=str(e))

        if self._scheduler_task and not self._scheduler_task.done():
            try:
                await asyncio.wait_for(self._scheduler_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("scheduler_task_shutdown_timeout")
                self._scheduler_task.cancel()
                await asyncio.gather(self._scheduler_task, return_exceptions=True)
            finally:
                self._scheduler_task = None

        try:
            await self._client.close()
        except Exception as e:
            logger.warning("binance_client_close_error", error=str(e))

        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        self._started = False
        logger.info("binance_rate_source_closed")

    async def _init_symbols(self) -> None:
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=2, max=10),
                retry=retry_if_exception_type(Exception),
            ):
                with attempt:
                    pairs = await self._get_latest_pairs()
                    self._set_tracked_pairs(pairs)
                    logger.info(
                        "binance_symbols_initialized",
                        pair_count=len(self._tracked_pairs),
                    )

        except RetryError as e:
            logger.error(
                "binance_symbols_init_failed_after_retries",
                error=str(e.last_attempt.exception()),
                exc_info=True,
            )
            raise

    async def _get_latest_pairs(self) -> list[Pair]:
        start_time = time.time()

        try:
            info = await self._client.get_exchange_info()
            pairs = [
                Pair(base=Currency(sym.base_asset), quote=Currency(sym.quote_asset))
                for sym in info.symbols
            ]

            duration = time.time() - start_time

            logger.debug(
                "binance_pairs_fetched",
                pair_count=len(pairs),
                duration_ms=round(duration * 1000, 2),
            )

            if settings.ENABLE_METRICS:
                metrics = get_metrics_registry()
                metrics.external_api_requests_total.labels(
                    provider="binance", endpoint="exchangeInfo", status="success"
                ).inc()
                metrics.external_api_duration_seconds.labels(
                    provider="binance", endpoint="exchangeInfo"
                ).observe(duration)

            return pairs

        except Exception as e:
            logger.error("binance_pairs_fetch_failed", error=str(e), exc_info=True)

            if settings.ENABLE_METRICS:
                metrics = get_metrics_registry()
                metrics.external_api_requests_total.labels(
                    provider="binance", endpoint="exchangeInfo", status="error"
                ).inc()

            raise

    def _set_tracked_pairs(self, pairs: list[Pair]) -> None:
        self._tracked_pairs = pairs

    async def _rates_tick(self) -> None:
        if not self._tracked_pairs:
            await self._offer_batch(RateBatch(quotes=[]))
            return

        start_time = time.time()

        try:
            server_time, tickers = await asyncio.gather(
                self._client.get_server_time(),
                self._client.get_all_ticker_prices(),
            )

            timestamp: TimestampUTC = self._mapper.to_timestamp(server_time)

            quotes: list[Quote] = self._mapper.tickers_to_quotes(
                tickers=tickers,
                pairs=self._tracked_pairs,
                timestamp=timestamp,
            )

            duration = time.time() - start_time

            logger.info(
                "binance_rates_fetched",
                quote_count=len(quotes),
                tracked_pairs=len(self._tracked_pairs),
                duration_ms=round(duration * 1000, 2),
            )

            if settings.ENABLE_METRICS:
                metrics = get_metrics_registry()
                metrics.quotes_fetched_total.labels(source="binance").inc(len(quotes))
                metrics.external_api_requests_total.labels(
                    provider="binance", endpoint="ticker/price", status="success"
                ).inc()
                metrics.external_api_duration_seconds.labels(
                    provider="binance", endpoint="ticker/price"
                ).observe(duration)

            if quotes:
                await self._offer_batch(RateBatch(quotes=quotes))
            else:
                logger.warning("no_valid_quotes_in_batch")

            if len(quotes) < len(self._tracked_pairs):
                missing = len(self._tracked_pairs) - len(quotes)
                logger.debug(
                    "binance_missing_or_invalid_tickers", missing_count=missing
                )

        except Exception as e:
            logger.error("binance_rates_fetch_failed", error=str(e), exc_info=True)

            if settings.ENABLE_METRICS:
                metrics = get_metrics_registry()
                metrics.external_api_requests_total.labels(
                    provider="binance", endpoint="ticker/price", status="error"
                ).inc()

    async def _symbols_tick(self) -> None:
        try:
            pairs = await self._get_latest_pairs()
            self._set_tracked_pairs(pairs)

            logger.info(
                "binance_symbols_refreshed", pair_count=len(self._tracked_pairs)
            )
        except Exception as e:
            logger.error("binance_symbols_refresh_failed", error=str(e), exc_info=True)

    async def _offer_batch(self, batch: RateBatch) -> None:
        if self._shutdown.is_set():
            return
        try:
            self._queue.put_nowait(batch)
        except asyncio.QueueFull:
            logger.warning("binance_queue_full_dropping_batch", quote_count=len(batch))
        except asyncio.CancelledError:
            pass
