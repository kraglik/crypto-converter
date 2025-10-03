from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import pytest
from converter.app.ports.outbound.quote_repository import QuoteRepository
from converter.app.queries.get_conversion import ConversionResult as AppConversionResult
from converter.app.queries.get_conversion import (
    GetConversionQuery,
    GetConversionQueryHandler,
)
from converter.domain.exceptions.conversion import QuoteNotFoundError
from converter.domain.models import Quote
from converter.domain.services.conversion_service import (
    ConversionResult as DomainConversionResult,
)
from converter.domain.services.conversion_service import (
    ConversionService,
)
from converter.domain.values import Amount, Currency, Pair, Rate, TimestampUTC


class MockQuoteRepository(QuoteRepository):
    def __init__(self, quote: Optional[Quote]):
        self.quote = quote
        self.calls = []

    async def get_latest(self, pair: Pair):
        self.calls.append(("get_latest", pair))
        return self.quote

    async def get_latest_before(self, pair: Pair, timestamp: TimestampUTC):
        self.calls.append(("get_latest_before", pair, timestamp))
        return self.quote


class MockConversionService(ConversionService):
    def __init__(self):
        pass

    def convert(
        self,
        amount: Amount,
        quote: Quote,
        reference_time: Optional[TimestampUTC] = None,
    ) -> DomainConversionResult:
        converted = Amount(amount.value * quote.rate.value)
        return DomainConversionResult(
            original_amount=amount,
            converted_amount=converted,
            quote=quote,
        )


def _quote() -> Quote:
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("25000")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc)),
    )


@pytest.mark.asyncio
async def test_handle_latest_happy_path():
    q = _quote()
    repo = MockQuoteRepository(quote=q)
    svc = MockConversionService()

    handler = GetConversionQueryHandler(quote_repository=repo, conversion_service=svc)

    query = GetConversionQuery(
        amount=Amount(Decimal("2")),
        pair=q.pair,
        at_timestamp=None,
    )

    result: AppConversionResult = await handler.handle(query)

    assert result.amount.value == Decimal("50000")
    assert result.original_amount.value == Decimal("2")
    assert result.rate.value == Decimal("25000")
    assert result.timestamp == q.timestamp

    assert repo.calls and repo.calls[0][0] == "get_latest"


@pytest.mark.asyncio
async def test_handle_historical_happy_path():
    q = _quote()
    repo = MockQuoteRepository(quote=q)
    svc = MockConversionService()
    handler = GetConversionQueryHandler(quote_repository=repo, conversion_service=svc)

    ref = TimestampUTC(datetime(2025, 10, 2, 12, 1, 0, tzinfo=timezone.utc))
    query = GetConversionQuery(
        amount=Amount(Decimal("1.5")), pair=q.pair, at_timestamp=ref
    )

    result = await handler.handle(query)

    assert result.amount.value == Decimal("37500")
    assert repo.calls and repo.calls[0][0] == "get_latest_before"


@pytest.mark.asyncio
async def test_handle_raises_when_quote_missing():
    repo = MockQuoteRepository(quote=None)
    svc = MockConversionService()
    handler = GetConversionQueryHandler(quote_repository=repo, conversion_service=svc)

    query = GetConversionQuery(
        amount=Amount(Decimal("1")),
        pair=Pair(Currency("ETH"), Currency("USDT")),
        at_timestamp=None,
    )

    with pytest.raises(QuoteNotFoundError):
        await handler.handle(query)
