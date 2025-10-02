from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class BinanceTicker:
    """
    Ticker price response from Binance API.

    https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints

    Endpoint: GET /api/v3/ticker/price
    This endpoint has a low 'weight', so it's fine to use it frequently.

    Example response (from the future, if Elon is right):
        {
            "symbol": "BTCUSDT",
            "price": "1000000.50000000"
        }
    """

    symbol: str
    price: Decimal

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if not self.symbol.isupper():
            raise ValueError(f"Symbol must be uppercase: {self.symbol}")

        if self.price < 0:
            raise ValueError(f"Price must be positive: {self.price}")

    @classmethod
    def from_json(cls, data: dict) -> "BinanceTicker":
        try:
            symbol = data["symbol"]
            price_str = data["price"]

            price = Decimal(price_str)

            return cls(symbol=symbol, price=price)

        except KeyError as e:
            raise ValueError(f"Missing required field in ticker response: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid ticker data: {e}") from e

    @classmethod
    def from_json_list(cls, data: list[dict[str, Any]]) -> list["BinanceTicker"]:
        return [cls.from_json(record) for record in data]

    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "price": str(self.price)}

    def __str__(self) -> str:
        return f"{self.symbol}: {self.price}"
