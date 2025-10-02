from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class BinanceServerTime:
    """
    Response from GET /api/v3/time

    https://developers.binance.com/docs/derivatives/option/market-data/Check-Server-Time
    NOTE: this is for /eapi/v1/time , but they have the same response format

    Example::
        {"serverTime": 1499827319559}
    """

    server_time_ms: int

    @property
    def as_datetime(self) -> datetime:
        """Convert millisecond timestamp to timezone-aware UTC datetime."""
        return datetime.fromtimestamp(self.server_time_ms / 1000, tz=timezone.utc)

    @classmethod
    def from_json(cls, data: dict) -> "BinanceServerTime":
        try:
            return cls(server_time_ms=int(data["serverTime"]))

        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid server time response: {e}") from e
