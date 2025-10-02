from datetime import datetime, timezone
from decimal import Decimal

import pytest

from converter.adapters.outbound.persistence.sqlalchemy.models import QuoteModel
from converter.adapters.outbound.persistence.sqlalchemy.quote_repository import (
    PostgresQuoteRepository,
)
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, TimestampUTC


class MockResult:
    def __init__(self, model):
        self._model = model

    def scalar_one_or_none(self):
        return self._model


class MockSession:
    def __init__(self, model):
        self._model = model
        self.executed = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, stmt):
        self.executed.append(stmt)
        return MockResult(self._model)


def _session_factory_with(model):
    def _factory():
        return MockSession(model)
    return _factory


@pytest.mark.asyncio
async def test_get_latest_returns_mapped_quote():
    # Given
    model = QuoteModel(
        symbol="BTCUSDT",
        quote_timestamp=datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc),
        base_currency="BTC",
        quote_currency="USDT",
        rate=Decimal("25000.00"),
    )
    repo = PostgresQuoteRepository(
        session_factory=_session_factory_with(model),
        rate_factory=RateFactory(PrecisionService()),
    )
    pair = Pair(Currency("BTC"), Currency("USDT"))

    # When
    q = await repo.get_latest(pair)

    # Then
    assert q is not None
    assert q.pair == pair
    assert q.rate.value == Decimal("25000.00")


@pytest.mark.asyncio
async def test_get_latest_before_none_when_not_found():
    # Given
    repo = PostgresQuoteRepository(
        session_factory=_session_factory_with(None),
        rate_factory=RateFactory(PrecisionService()),
    )
    pair = Pair(Currency("ETH"), Currency("USDT"))
    ts = TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc))

    # Whe
    q = await repo.get_latest_before(pair, ts)

    # Then
    assert q is None