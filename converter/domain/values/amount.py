from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Amount:
    value: Decimal

    def __post_init__(self):
        if self.value < 0:
            raise ValueError(f"Amount cannot be negative: {self.value}")

    def __mul__(self, other: Decimal) -> "Amount":
        return Amount(self.value * other)

    def __str__(self) -> str:
        return str(self.value)

    def is_zero(self) -> bool:
        return self.value == 0
