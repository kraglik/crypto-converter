from dataclasses import dataclass


@dataclass(frozen=True)
class BinanceSymbolInfo:
    """
    Symbol information from Binance exchange info.

    Endpoint: GET /api/v3/exchangeInfo
    """

    symbol: str
    base_asset: str
    quote_asset: str

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("Symbol cannot be empty")
        if not self.symbol.isupper():
            raise ValueError(f"Symbol must be uppercase: {self.symbol}")

        if not self.base_asset:
            raise ValueError("Base asset cannot be empty")
        if not self.quote_asset:
            raise ValueError("Quote asset cannot be empty")

        expected = f"{self.base_asset}{self.quote_asset}"

        if self.symbol != expected:
            raise ValueError(
                f"Symbol '{self.symbol}' doesn't match "
                f"base '{self.base_asset}' + quote '{self.quote_asset}' = '{expected}'"
            )

    @classmethod
    def from_json(cls, data: dict) -> "BinanceSymbolInfo":
        try:
            return cls(
                symbol=data["symbol"],
                base_asset=data["baseAsset"],
                quote_asset=data["quoteAsset"],
            )

        except KeyError as e:
            raise ValueError(f"Missing required field in symbol info: {e}") from e
