import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

try:
    from fakeredis.aioredis import FakeRedis  # fakeredis>=2.x
except Exception:
    FakeRedis = None

from converter.adapters.outbound.persistence.redis.quote_repository import (
    RedisQuoteRepository,
)
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, TimestampUTC

pytestmark = pytest.mark.skipif(FakeRedis is None, reason="fakeredis not available")


@pytest.mark.asyncio
async def test_get_latest_hit_and_miss():
    # When
    redis = FakeRedis()
    repo = RedisQuoteRepository(redis_client=redis, rate_factory=RateFactory(PrecisionService()))

    pair = Pair(Currency("BTC"), Currency("USDT"))
    key = f"quote:latest:{pair}"

    payload = {
        "symbol": "BTCUSDT",
        "rate": "25000.5",
        "timestamp": datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc).isoformat(),
    }

    # When
    await redis.set(key, json.dumps(payload))

    q = await repo.get_latest(pair)
    other = Pair(Currency("ETH"), Currency("USDT"))
    q2 = await repo.get_latest(other)

    # THen
    assert q is not None
    assert q.pair == pair
    assert q.rate.value == Decimal("25000.5")
    assert q2 is None


@pytest.mark.asyncio
async def test_get_latest_before_not_supported():
    # Given
    redis = FakeRedis()
    repo = RedisQuoteRepository(redis_client=redis, rate_factory=RateFactory(PrecisionService()))
    pair = Pair(Currency("BTC"), Currency("USDT"))
    ts = TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc))

    # When
    q = await repo.get_latest_before(pair, ts)

    # Then
    assert q is None