from dataclasses import dataclass
from typing import Optional

from converter.app.ports.outbound.quote_repository import QuoteRepository
from converter.domain.exceptions.conversion import QuoteNotFoundError
from converter.domain.models import Quote
from converter.domain.services import ConversionService
from converter.domain.values import Amount, Pair, Rate, TimestampUTC


@dataclass(frozen=True)
class GetConversionQuery:
    amount: Amount
    pair: Pair
    at_timestamp: Optional[TimestampUTC] = None


@dataclass(frozen=True)
class ConversionResult:
    amount: Amount
    original_amount: Amount
    rate: Rate
    timestamp: TimestampUTC


class GetConversionQueryHandler:
    def __init__(
        self,
        quote_repository: QuoteRepository,
        conversion_service: ConversionService,
    ):
        self._repository = quote_repository
        self._conversion_service = conversion_service

    async def handle(self, query: GetConversionQuery) -> ConversionResult:
        """
        Convert an amount using provided quote.
        For historical conversions, appropriate reference time must be provided.

        :param query: Query with the conversion data to be processed.
        :return: ConversionResult with conversion data

        :raises QuoteTooOldError: If fetched quote is too old
        :raises QuoteNotFoundError: If no matching quote is found
        """
        quote = await self._get_quote(query)

        return self._convert(quote, query)

    async def _get_quote(self, query: GetConversionQuery) -> Quote:
        if query.at_timestamp is None:
            quote = await self._repository.get_latest(query.pair)
        else:
            quote = await self._repository.get_latest_before(
                query.pair, query.at_timestamp
            )

        if quote is not None:
            return quote

        raise QuoteNotFoundError(query.pair)

    def _convert(self, quote: Quote, query: GetConversionQuery) -> ConversionResult:
        conversion_result = self._conversion_service.convert(
            query.amount, quote, reference_time=query.at_timestamp
        )

        return ConversionResult(
            amount=conversion_result.converted_amount,
            original_amount=conversion_result.original_amount,
            rate=conversion_result.rate,
            timestamp=conversion_result.timestamp,
        )
