from typing import Optional

from converter.domain.exceptions.base import DomainException
from converter.domain.values import Pair, QuoteAge, TimestampUTC


class ConversionError(DomainException):
    pass


class QuoteNotFoundError(ConversionError):
    """Raised when no quote is available for a currency pair."""

    def __init__(self, pair: Pair, timestamp: Optional["TimestampUTC"] = None):
        message = f"No quote found for pair {pair}"

        if timestamp:
            message += f" at {timestamp}"

        super().__init__(message)


class QuoteTooOldError(ConversionError):
    """Raised when available quote is too old to use."""

    def __init__(
        self,
        pair: Pair,
        age: QuoteAge,
        max_age_seconds: int,
        reference_time: Optional[TimestampUTC] = None,
    ):
        message = (
            f"Quote for {pair} is too old: {age.seconds:.1f}s old, "
            f"max_age_seconds: {max_age_seconds} seconds"
        )

        if reference_time is not None:
            message += f", at {reference_time}"

        super().__init__(message)


class UnsupportedPairError(ConversionError):
    """Raised when currency pair is not supported."""

    def __init__(self, pair: Pair):
        self.pair = pair

        super().__init__(f"Currency pair {pair} is not supported")


class InvalidConversionError(ConversionError):
    """Raised when conversion parameters are invalid."""

    def __init__(self, reason: str):
        super().__init__(
            f"Invalid conversion: {reason}",
        )
