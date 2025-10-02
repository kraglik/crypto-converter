import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from converter.adapters.inbound.consumer.quote_consumer import QuoteConsumer
from converter.adapters.outbound.rate_source import RateBatch
from converter.app.commands.store_quotes import StoreQuotesCommandHandler
from converter.domain.models import Quote
from converter.domain.values import Currency, Pair, Rate, TimestampUTC


class MockRateSource:
    def __init__(self):
        self.queue: asyncio.Queue[RateBatch] = asyncio.Queue()
        self.closed = False

    async def stream(self):
        while not self.closed:
            try:
                batch = await asyncio.wait_for(self.queue.get(), timeout=0.1)
                yield batch
            except asyncio.TimeoutError:
                if self.closed:
                    break
                continue

    async def close(self):
        self.closed = True


class MockHandler(StoreQuotesCommandHandler):
    def __init__(self):
        self.calls: list[int] = []

    async def handle(self, command):
        self.calls.append(len(command.quotes))
        class R:
            total_received = len(command.quotes)
        return R()


def _q():
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("25000")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 0, 0, tzinfo=timezone.utc)),
    )


@pytest.mark.asyncio
async def test_consumer_processes_non_empty_batches_and_skips_empty():
    # Given
    src = MockRateSource()
    handler = MockHandler()
    consumer = QuoteConsumer(rate_source=src, handler=handler)

    # When
    await src.queue.put(RateBatch(quotes=[_q()]))
    await src.queue.put(RateBatch(quotes=[]))
    await src.queue.put(RateBatch(quotes=[_q(), _q()]))

    task = asyncio.create_task(consumer.start())
    await asyncio.sleep(0.2)
    await consumer.stop()
    await asyncio.wait_for(task, timeout=1.0)

    # Then
    assert handler.calls == [1, 2]