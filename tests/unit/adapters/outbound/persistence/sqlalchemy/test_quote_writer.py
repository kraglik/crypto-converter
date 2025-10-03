from datetime import datetime, timezone
from decimal import Decimal

import pytest
from converter.adapters.outbound.persistence.sqlalchemy.quote_writer import (
    PostgresQuoteWriter,
)
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, Rate, TimestampUTC


class DummyResult:
    pass


class DummyBegin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DummySession:
    def __init__(self):
        self.executed = []
        self._begins = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def begin(self):
        self._begins += 1
        return DummyBegin()

    async def execute(self, stmt):
        self.executed.append(stmt)
        return DummyResult()


def _session_factory():
    def _factory():
        return DummySession()

    return _factory


def _q():
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("25000.00")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc)),
    )


@pytest.mark.asyncio
async def test_save_batch_executes_insert_once():
    writer = PostgresQuoteWriter(
        session_factory=_session_factory(),
        rate_factory=RateFactory(PrecisionService()),
    )

    quotes = [_q(), _q()]
    await writer.save_batch(quotes)
