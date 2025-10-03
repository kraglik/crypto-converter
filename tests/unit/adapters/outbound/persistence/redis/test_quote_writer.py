import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

try:
    from fakeredis.aioredis import FakeRedis
except Exception:
    FakeRedis = None

from converter.adapters.outbound.persistence.redis.quote_writer import RedisQuoteWriter
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, Rate, TimestampUTC

pytestmark = pytest.mark.skipif(FakeRedis is None, reason="fakeredis not available")


def _q():
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("25000")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc)),
    )


@pytest.mark.asyncio
async def test_redis_writer_saves_with_ttl():
    # Given
    redis = FakeRedis()
    writer = RedisQuoteWriter(
        redis_client=redis, rate_factory=RateFactory(PrecisionService()), ttl_seconds=90
    )
    quotes = [_q(), _q()]
    key = f"quote:latest:{quotes[0].pair}"

    # When
    await writer.save_batch(quotes)
    val = await redis.get(key)

    assert val is not None

    payload = json.loads(val)
    ttl = await redis.ttl(key)

    # Then
    assert payload["symbol"] == "BTCUSDT"
    assert payload["rate"] == "25000"
    assert "timestamp" in payload
    assert 0 < ttl <= 90


@pytest.mark.asyncio
async def test_redis_writer_empty_batch_noop():
    # Given
    redis = FakeRedis()
    writer = RedisQuoteWriter(
        redis_client=redis, rate_factory=RateFactory(PrecisionService()), ttl_seconds=60
    )

    # When & Then
    await writer.save_batch([])
