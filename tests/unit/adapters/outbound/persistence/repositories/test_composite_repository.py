from datetime import datetime, timezone
from decimal import Decimal

import pytest
from converter.adapters.outbound.persistence.repositories.composite_quote_repository import (
    CompositeQuoteRepository,
)
from converter.app.ports.outbound.quote_repository import QuoteRepository
from converter.domain.models import Quote
from converter.domain.values import Currency, Pair, Rate, TimestampUTC


class MockRepo(QuoteRepository):
    def __init__(self, latest=None, latest_before=None):
        self.latest = latest
        self.latest_before = latest_before
        self.calls = []

    async def get_latest(self, pair: Pair):
        self.calls.append(("get_latest", pair))
        return self.latest

    async def get_latest_before(self, pair: Pair, timestamp: TimestampUTC):
        self.calls.append(("get_latest_before", pair, timestamp))
        return self.latest_before


def _quote():
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("100")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 0, 0, tzinfo=timezone.utc)),
    )


@pytest.mark.asyncio
async def test_composite_repo_uses_primary_when_hit():
    # Given
    q = _quote()
    primary = MockRepo(latest=q)
    fallback = MockRepo()
    repo = CompositeQuoteRepository(primary, fallback)
    pair = q.pair

    # When
    res = await repo.get_latest(pair)

    # Then
    assert res == q
    assert primary.calls and primary.calls[0][0] == "get_latest"
    assert not fallback.calls


@pytest.mark.asyncio
async def test_composite_repo_falls_back_when_miss():
    # Given
    q = _quote()
    primary = MockRepo(latest=None)
    fallback = MockRepo(latest=q)
    repo = CompositeQuoteRepository(primary, fallback)

    # When
    res = await repo.get_latest(q.pair)

    # Then
    assert res == q
    assert primary.calls and fallback.calls


@pytest.mark.asyncio
async def test_composite_repo_historical_uses_fallback_only():
    # Given
    q = _quote()
    ts = TimestampUTC(datetime(2025, 10, 2, 1, 0, tzinfo=timezone.utc))
    primary = MockRepo()
    fallback = MockRepo(latest_before=q)

    # When
    repo = CompositeQuoteRepository(primary, fallback)
    res = await repo.get_latest_before(q.pair, ts)

    # Then
    assert res == q
    assert fallback.calls and fallback.calls[0][0] == "get_latest_before"
