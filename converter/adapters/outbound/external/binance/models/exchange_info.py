from dataclasses import dataclass

from .symbol import BinanceSymbolInfo


@dataclass(frozen=True)
class BinanceExchangeInfo:
    """
    Exchange info from Binance.

    Endpoint: GET /api/v3/exchangeInfo
    """

    symbols: list[BinanceSymbolInfo]

    @classmethod
    def from_json(cls, data: dict) -> "BinanceExchangeInfo":
        try:
            symbols_data = data["symbols"]

            if not isinstance(symbols_data, list):
                raise ValueError("symbols must be a list!!")

            return BinanceExchangeInfo(
                [BinanceSymbolInfo.from_json(record) for record in symbols_data]
            )

        except KeyError as e:
            raise ValueError(f"Missing required field in exchange info: {e}") from e
