from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class RedisTicker:
    symbol: str
    rate: Decimal
    timestamp: datetime

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if not self.symbol.isupper():
            raise ValueError(f"Symbol must be uppercase: {self.symbol}")

        if self.rate < 0:
            raise ValueError(f"Price must be positive: {self.rate}")

    @classmethod
    def from_dict(cls, data: dict) -> "RedisTicker":
        try:
            symbol = data["symbol"]
            price_str = data["rate"]
            timestamp = datetime.fromisoformat(data["timestamp"])

            rate = Decimal(price_str)

            return cls(symbol=symbol, rate=rate, timestamp=timestamp)

        except KeyError as e:
            raise ValueError(f"Missing required field in ticker response: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid ticker data: {e}") from e
        except InvalidOperation as e:
            raise ValueError(f"Invalid rate data: {e}") from e

    def to_dict(self) -> dict:
        return {
            "symbol": str(self.symbol),
            "rate": str(self.rate),
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        return f"{self.symbol}: {self.rate}"
