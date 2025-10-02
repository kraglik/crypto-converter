from datetime import datetime, timezone
from decimal import Decimal

from converter.adapters.outbound.external.binance.mapper import BinanceMapper
from converter.adapters.outbound.external.binance.models import (
    BinanceServerTime,
    BinanceSymbolInfo,
    BinanceTicker,
)
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, TimestampUTC


def test_mapper_tickers_to_quotes_filters_invalid_and_zero():
    # Given
    mapper = BinanceMapper(rate_factory=RateFactory(PrecisionService()))
    pairs = [
        Pair(Currency("BTC"), Currency("USDT")),
        Pair(Currency("ETH"), Currency("USDT")),
    ]
    tickers = [
        BinanceTicker(symbol="BTCUSDT", price=Decimal("25000")),
        BinanceTicker(symbol="ETHUSDT", price=Decimal("0")),  # zero excluded
    ]
    ts = TimestampUTC(datetime(2025, 10, 2, 0, 0, tzinfo=timezone.utc))

    # When
    quotes = mapper.tickers_to_quotes(tickers, pairs, ts)

    # Then
    assert len(quotes) == 1
    assert quotes[0].pair == pairs[0]
    assert quotes[0].rate.value == Decimal("25000")


def test_mapper_to_timestamp_and_pair():
    # Given
    mapper = BinanceMapper(rate_factory=RateFactory(PrecisionService()))
    st = BinanceServerTime(server_time_ms=1700000000000)
    sym = BinanceSymbolInfo(symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT")

    # When
    ts = mapper.to_timestamp(st)
    pair = mapper.to_pair(sym)

    # Then
    assert isinstance(ts, TimestampUTC)
    assert str(pair) == "BTCUSDT"