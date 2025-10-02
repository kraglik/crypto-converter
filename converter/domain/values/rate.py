from dataclasses import dataclass
from decimal import Decimal

from .amount import Amount


@dataclass(frozen=True)
class Rate:
    value: Decimal

    def __post_init__(self):
        if self.value <= 0:
            raise ValueError(f"Rate must be positive: {self.value}")

    def __str__(self) -> str:
        return str(self.value)

    def apply_to(self, amount: Amount) -> Amount:
        return amount * self.value

    def inverse(self) -> "Rate":
        return Rate(Decimal("1") / self.value)
