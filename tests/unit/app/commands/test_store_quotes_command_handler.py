from datetime import datetime, timezone
from decimal import Decimal

import pytest

from converter.app.commands.store_quotes import (
    StoreQuotesCommand,
    StoreQuotesCommandHandler,
)
from converter.app.ports.outbound.quote_repository import QuoteWriter
from converter.domain.models import Quote
from converter.domain.values import Currency, Pair, Rate, TimestampUTC


class MockWriter(QuoteWriter):
    def __init__(self):
        self.saved_batches: list[list[Quote]] = []

    async def save_batch(self, quotes: list[Quote]) -> None:
        self.saved_batches.append(quotes)


def _q():
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("25000")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc)),
    )


@pytest.mark.asyncio
async def test_store_quotes_calls_writer_and_counts():
    writer = MockWriter()
    handler = StoreQuotesCommandHandler(quote_writer_factory=writer)

    quotes = [_q(), _q()]
    cmd = StoreQuotesCommand(quotes=quotes)

    result = await handler.handle(cmd)

    assert result.total_received == 2
    assert len(writer.saved_batches) == 1
    assert writer.saved_batches[0] == quotes