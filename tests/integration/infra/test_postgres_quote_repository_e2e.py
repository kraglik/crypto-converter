from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from converter.adapters.outbound.persistence.sqlalchemy.quote_repository import (
    PostgresQuoteRepository,
)
from converter.adapters.outbound.persistence.sqlalchemy.quote_writer import (
    PostgresQuoteWriter,
)
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, Rate, TimestampUTC
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


def _quote(ts: datetime) -> Quote:
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("25000.00")),
        timestamp=TimestampUTC(ts),
    )


@pytest.mark.asyncio
async def test_postgres_writer_and_repository_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
):
    # Given
    rate_factory = RateFactory(PrecisionService())
    writer = PostgresQuoteWriter(
        session_factory=session_factory, rate_factory=rate_factory
    )
    repo = PostgresQuoteRepository(
        session_factory=session_factory, rate_factory=rate_factory
    )

    base_time = datetime.now(timezone.utc).replace(microsecond=0)
    q1 = _quote(base_time - timedelta(seconds=30))
    q2 = _quote(base_time - timedelta(seconds=10))

    # When
    await writer.save_batch([q1, q2])

    latest = await repo.get_latest(q2.pair)
    before = await repo.get_latest_before(
        q2.pair, TimestampUTC(base_time - timedelta(seconds=20))
    )

    # Then
    assert latest is not None
    assert latest.timestamp.value == q2.timestamp.value
    assert latest.rate.value == Decimal("25000.00")

    assert before is not None
    assert before.timestamp.value == q1.timestamp.value
