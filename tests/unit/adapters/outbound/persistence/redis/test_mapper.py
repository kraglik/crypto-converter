from datetime import datetime, timezone
from decimal import Decimal

from converter.adapters.outbound.persistence.redis.mapper import RedisMapper
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, Rate, TimestampUTC


def test_redis_mapper_roundtrip():
    # Given
    mapper = RedisMapper(rate_factory=RateFactory(PrecisionService()))

    quote = Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("25000.12345678")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc)),
    )

    # When
    ticker = mapper.map_quote_to_ticker(quote)
    q2 = mapper.map_ticker_to_quote(ticker, pair=quote.pair)

    # Then
    assert ticker.symbol == "BTCUSDT"
    assert ticker.rate == Decimal("25000.12345678")
    assert ticker.timestamp.tzinfo == timezone.utc

    assert q2.pair == quote.pair
    assert q2.rate.value == quote.rate.value
    assert q2.timestamp.value == quote.timestamp.value
