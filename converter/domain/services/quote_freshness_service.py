from dataclasses import dataclass
from typing import Optional

from converter.domain.exceptions.conversion import QuoteTooOldError
from converter.domain.models import Quote
from converter.domain.values import TimestampUTC


@dataclass(frozen=True)
class FreshnessPolicy:
    max_age_seconds: int = 60

    def __post_init__(self):
        if self.max_age_seconds <= 0:
            raise ValueError(f"Max age must be positive: {self.max_age_seconds}")


class QuoteFreshnessService:
    def __init__(self, policy: FreshnessPolicy = None):
        self._policy = policy or FreshnessPolicy()

    def validate_freshness(
        self, quote: Quote, reference_time: Optional[TimestampUTC] = None
    ) -> None:
        """
        Validate whether a quote is fresh enough to use.

        :param quote: Quote to validate
        :param reference_time: Time to validate against (Optional, defaults to utc now)

        :raises QuoteTooOldError: if the quote in question is too old to be used
        """
        age = quote.age(reference_time)

        if age.is_stale(self._policy.max_age_seconds):
            raise QuoteTooOldError(
                pair=quote.pair,
                age=age,
                max_age_seconds=self._policy.max_age_seconds,
                reference_time=reference_time,
            )

    def is_fresh(self, quote: Quote, reference_time: TimestampUTC = None) -> bool:
        """
        Check if quote is fresh enough, but without raising exception.

        :param quote: Quote to check
        :param reference_time: Time to check against (default: now)

        :return: bool(is_fresh)
        """
        try:
            self.validate_freshness(quote, reference_time)
            return True
        except QuoteTooOldError:
            return False

    def filter_fresh_quotes(
        self, quotes: list[Quote], reference_time: TimestampUTC = None
    ) -> list[Quote]:
        """
        Filter a list of quotes to only fresh ones.
        After all, even querying an external service for new quotas takes time.

        :param quotes: List of quotes to filter
        :param reference_time: Time to check against (default: now)

        :return: List of fresh quotes, filtered from the original list.
        """
        return [q for q in quotes if self.is_fresh(q, reference_time)]
