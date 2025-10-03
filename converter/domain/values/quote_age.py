from dataclasses import dataclass

from .timestamp_utc import TimestampUTC


@dataclass(frozen=True)
class QuoteAge:
    seconds: float

    def __post_init__(self) -> None:
        if self.seconds < 0:
            raise ValueError(f"Quote age cannot be negative: {self.seconds}")

    def is_fresh(self, max_age_seconds: int) -> bool:
        return self.seconds <= max_age_seconds

    def is_stale(self, max_age_seconds: int) -> bool:
        return not self.is_fresh(max_age_seconds)

    @classmethod
    def between(
        cls, quote_time: TimestampUTC, reference_time: TimestampUTC
    ) -> "QuoteAge":
        seconds = (reference_time.value - quote_time.value).total_seconds()

        return cls(seconds)

    @classmethod
    def since(cls, quote_time: TimestampUTC) -> "QuoteAge":
        return cls.between(quote_time, TimestampUTC.now())
