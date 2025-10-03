from dataclasses import dataclass
from typing import Optional

from converter.domain.values import Amount, Pair, QuoteAge, Rate, TimestampUTC


# Well, we only need one business-level model so far.
@dataclass(frozen=True)
class Quote:
    """
    The Quote model.
    It represents a single quote for a given pair at a provided timestamp,
    and contains a conversion rate for the pair in question.
    """

    pair: Pair
    rate: Rate
    timestamp: TimestampUTC

    def age(self, reference_time: Optional[TimestampUTC] = None) -> QuoteAge:
        """
        Get the quote age.

        :param reference_time: Reference time for age calculation (default: utc now)
        :return: QuoteAge value object
        """
        if reference_time is None:
            return QuoteAge.since(self.timestamp)

        return QuoteAge.between(self.timestamp, reference_time)

    def convert(self, amount: Amount) -> Amount:
        """
        Convert an amount using this quote's rate.

        :param amount: Amount to convert
        :return: Converted amount
        """
        return self.rate.apply_to(amount)

    def __str__(self) -> str:
        return f"Quote({self.pair}, rate={self.rate}, at={self.timestamp})"
