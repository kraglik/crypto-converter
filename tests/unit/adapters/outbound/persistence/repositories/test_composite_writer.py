import types
from datetime import datetime, timezone
from decimal import Decimal

import converter.adapters.outbound.persistence.repositories.composite_quote_writer as writer_module
import pytest
from converter.adapters.outbound.persistence.repositories.composite_quote_writer import (
    CompositeQuoteWriter,
)
from converter.domain.models import Quote
from converter.domain.values import Currency, Pair, Rate, TimestampUTC


class MockWriter:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.saved = []

    async def save_batch(self, quotes: list[Quote]) -> None:
        if self.should_fail:
            raise RuntimeError("secondary fail")
        self.saved.append(quotes)


def _q():
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("1")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 0, 0, tzinfo=timezone.utc)),
    )


@pytest.mark.asyncio
async def test_composite_writer_calls_both():
    # Given
    primary = MockWriter()
    secondary = MockWriter()
    writer = CompositeQuoteWriter(primary, secondary)
    quotes = [_q(), _q()]

    # When
    await writer.save_batch(quotes)

    # Then
    assert len(primary.saved) == 1
    assert len(secondary.saved) == 1
    assert primary.saved[0] == quotes
    assert secondary.saved[0] == quotes


@pytest.mark.asyncio
async def test_composite_writer_swallows_secondary_errors(monkeypatch):
    # Given
    monkeypatch.setattr(
        writer_module,
        "settings",
        types.SimpleNamespace(ENABLE_METRICS=False),
        raising=False,
    )

    primary = MockWriter()
    secondary = MockWriter(should_fail=True)
    writer = CompositeQuoteWriter(primary, secondary)
    quotes = [_q()]

    # When
    await writer.save_batch(quotes)

    # THen
    assert len(primary.saved) == 1
    assert len(secondary.saved) == 0
