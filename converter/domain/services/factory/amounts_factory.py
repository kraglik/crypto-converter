from decimal import Decimal

from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Amount


class AmountFactory:
    def __init__(self, precision_service: PrecisionService):
        self._precision = precision_service

    def create(self, value: Decimal) -> Amount:
        normalized = self._precision.normalize_amount(value)
        return Amount(normalized)

    def from_string(self, value: str) -> Amount:
        return self.create(Decimal(value))

    def from_float(self, value: float) -> Amount:
        return self.create(Decimal(str(value)))
