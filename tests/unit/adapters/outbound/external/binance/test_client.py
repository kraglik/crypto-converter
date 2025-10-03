import pytest
from converter.adapters.outbound.external.binance.client import (
    BinanceAPIClient,
    BinanceEndpoint,
)
from converter.domain.exceptions.quote_provider import QuoteProviderUnavailableError


@pytest.mark.asyncio
async def test_binance_client_parses_server_time(monkeypatch):
    client = BinanceAPIClient(enable_circuit_breaker=False)

    async def fake_make_request(self, endpoint, params, description):
        assert endpoint == BinanceEndpoint.TIME
        return {"serverTime": 1700000000000}

    monkeypatch.setattr(BinanceAPIClient, "_make_request", fake_make_request)
    try:
        result = await client.get_server_time()
        assert result.server_time_ms == 1700000000000
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_binance_client_parses_exchange_info(monkeypatch):
    client = BinanceAPIClient(enable_circuit_breaker=False)

    async def fake_make_request(self, endpoint, params, description):
        assert endpoint == BinanceEndpoint.EXCHANGE_INFO
        return {
            "symbols": [{"symbol": "BTCUSDT", "baseAsset": "BTC", "quoteAsset": "USDT"}]
        }

    monkeypatch.setattr(BinanceAPIClient, "_make_request", fake_make_request)
    try:
        info = await client.get_exchange_info()
        assert len(info.symbols) == 1
        assert info.symbols[0].symbol == "BTCUSDT"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_binance_client_parses_tickers(monkeypatch):
    client = BinanceAPIClient(enable_circuit_breaker=False)

    async def fake_make_request(self, endpoint, params, description):
        assert endpoint == BinanceEndpoint.TICKER_PRICE
        return [{"symbol": "BTCUSDT", "price": "25000.0"}]

    monkeypatch.setattr(BinanceAPIClient, "_make_request", fake_make_request)
    try:
        tickers = await client.get_all_ticker_prices()
        assert len(tickers) == 1
        assert tickers[0].symbol == "BTCUSDT"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_binance_client_circuit_breaker_opens(monkeypatch):
    client = BinanceAPIClient(
        enable_circuit_breaker=True,
        circuit_breaker_failure_threshold=2,
        circuit_breaker_recovery_timeout=9999,
    )

    async def failing(self, endpoint, params, description):
        raise QuoteProviderUnavailableError("Binance", "fail")

    monkeypatch.setattr(BinanceAPIClient, "_make_request", failing)

    with pytest.raises(QuoteProviderUnavailableError):
        await client.get_server_time()
    with pytest.raises(QuoteProviderUnavailableError):
        await client.get_server_time()

    with pytest.raises(QuoteProviderUnavailableError) as exc:
        await client.get_server_time()

    assert "Circuit breaker is open" in str(exc.value)
    await client.close()
