import asyncio
from decimal import Decimal

import pytest
from converter.adapters.outbound.external.binance.models import (
    BinanceExchangeInfo,
    BinanceServerTime,
    BinanceSymbolInfo,
    BinanceTicker,
)
from converter.adapters.outbound.external.binance.rate_source import (
    BinanceStreamingRateSource,
)
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService


class MockScheduler:
    def __init__(self):
        self._jobs: list[tuple[str, int, callable]] = []

    def schedule(self, coro_func, interval_seconds: int, name: str):
        self._jobs.append((name, interval_seconds, coro_func))

    async def run_until_shutdown(self):
        for _, _, coro in list(self._jobs):
            await coro()

    async def shutdown(self):
        return


class MockClient:
    def __init__(self):
        self.calls = {"exchangeInfo": 0, "time": 0, "ticker": 0}

    async def get_exchange_info(self):
        self.calls["exchangeInfo"] += 1
        return BinanceExchangeInfo(
            symbols=[
                BinanceSymbolInfo(
                    symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT"
                ),
                BinanceSymbolInfo(
                    symbol="ETHUSDT", base_asset="ETH", quote_asset="USDT"
                ),
            ]
        )

    async def get_server_time(self):
        self.calls["time"] += 1
        return BinanceServerTime(server_time_ms=1700000000000)

    async def get_all_ticker_prices(self):
        self.calls["ticker"] += 1
        return [
            BinanceTicker(symbol="BTCUSDT", price=Decimal("25000")),
            BinanceTicker(symbol="ETHUSDT", price=Decimal("0")),
        ]

    async def close(self):
        return


@pytest.mark.asyncio
async def test_rate_source_stream_yields_batch_without_private_access():
    client = MockClient()
    rate_factory = RateFactory(PrecisionService())
    scheduler = MockScheduler()

    src = BinanceStreamingRateSource(
        api_client=client,
        rate_factory=rate_factory,
        rates_interval_seconds=1,
        symbols_interval_seconds=5,
        queue_maxsize=10,
        scheduler=scheduler,
    )

    async def first_batch():
        agen = src.stream()

        try:
            return await asyncio.wait_for(anext(agen), timeout=1.0)
        finally:
            await src.close()

    batch = await first_batch()

    assert len(batch.quotes) == 1
    assert str(batch.quotes[0].pair) == "BTCUSDT"
