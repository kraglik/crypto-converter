from dataclasses import dataclass

from .currency import Currency


@dataclass(frozen=True)
class Pair:
    base: Currency
    quote: Currency

    def __post_init__(self):
        if self.base == self.quote:
            raise ValueError(
                f"Base and quote currencies must be different: {self.base}"
            )

    def __str__(self) -> str:
        return f"{self.base}{self.quote}"

    def inverse(self) -> "Pair":
        """Returns the inverse variant of the current pair (BTC/USD -> USD/BTC)."""
        return Pair(base=self.quote, quote=self.base)

    def code(self) -> str:
        """Returns the code of the pair (BTC/USD -> 'BTCUSD')."""
        return self.base.code + self.quote.code
