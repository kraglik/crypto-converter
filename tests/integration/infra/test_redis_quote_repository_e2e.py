from datetime import datetime, timezone
from decimal import Decimal

import pytest
import redis.asyncio as aioredis
from converter.adapters.outbound.persistence.redis.quote_repository import (
    RedisQuoteRepository,
)
from converter.adapters.outbound.persistence.redis.quote_writer import RedisQuoteWriter
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, Rate, TimestampUTC


def _quote(ts: datetime) -> Quote:
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("25000")),
        timestamp=TimestampUTC(ts),
    )


@pytest.mark.asyncio
async def test_redis_writer_and_repo_roundtrip(redis_client: aioredis.Redis):
    # Given
    rate_factory = RateFactory(PrecisionService())
    writer = RedisQuoteWriter(
        redis_client=redis_client, rate_factory=rate_factory, ttl_seconds=120
    )
    repo = RedisQuoteRepository(redis_client=redis_client, rate_factory=rate_factory)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    q = _quote(now)

    # Whe
    await writer.save_batch([q])

    got = await repo.get_latest(q.pair)
    key = f"quote:latest:{q.pair}"
    ttl = await redis_client.ttl(key)

    # Then
    assert got is not None
    assert got.pair == q.pair
    assert got.rate.value == Decimal("25000")
    assert got.timestamp.value == q.timestamp.value
    assert ttl > 0
