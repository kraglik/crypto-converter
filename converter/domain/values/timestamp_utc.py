from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True)
class TimestampUTC:
    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None:
            dt_utc = self.value.replace(tzinfo=timezone.utc)
        else:
            dt_utc = self.value.astimezone(timezone.utc)

        object.__setattr__(self, "value", dt_utc)

    def __str__(self) -> str:
        return self.value.isoformat()

    def age_seconds(self, reference: Optional["TimestampUTC"] = None) -> float:
        if reference is None:
            reference = TimestampUTC.now()
        return (reference.value - self.value).total_seconds()

    def is_older_than_seconds(
        self, seconds: int, reference: Optional["TimestampUTC"] = None
    ) -> bool:
        return self.age_seconds(reference) > seconds

    @classmethod
    def now(cls) -> "TimestampUTC":
        return cls(datetime.now(timezone.utc))

    @classmethod
    def from_timestamp(cls, timestamp: float) -> "TimestampUTC":
        return cls(datetime.fromtimestamp(timestamp, tz=timezone.utc))

    @classmethod
    def from_iso_string(cls, iso_string: str) -> "TimestampUTC":
        return cls(datetime.fromisoformat(iso_string))
