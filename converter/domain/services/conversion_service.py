from dataclasses import dataclass

from converter.domain.models import Quote
from converter.domain.values import Amount, Pair, Rate, TimestampUTC

from .quote_freshness_service import QuoteFreshnessService


@dataclass(frozen=True)
class ConversionResult:
    original_amount: Amount
    converted_amount: Amount
    quote: Quote

    @property
    def pair(self) -> Pair:
        return self.quote.pair

    @property
    def rate(self) -> Rate:
        return self.quote.rate

    @property
    def timestamp(self) -> TimestampUTC:
        return self.quote.timestamp


class ConversionService:
    def __init__(self, freshness_service: QuoteFreshnessService):
        self._freshness_service = freshness_service

    def convert(
        self, amount: Amount, quote: Quote, reference_time: TimestampUTC = None
    ) -> ConversionResult:
        """
        Convert an amount using provided quote.
        For historical conversions, appropriate reference time must be provided.

        :param amount: Amount that needs to be converted.
        :param quote: Quote object, either a fresh one or the most recent for the reference time provided.
        :param reference_time: Reference time for freshness check

        :return: ConversionResult with converted amount and metadata

        :raises QuoteTooOldError: If quote is too old :-)
        """
        self._freshness_service.validate_freshness(quote, reference_time)

        converted_amount = quote.convert(amount)

        return ConversionResult(
            original_amount=amount, converted_amount=converted_amount, quote=quote
        )
