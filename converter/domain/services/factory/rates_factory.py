from decimal import Decimal

from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Rate


class RateFactory:
    def __init__(self, precision_service: PrecisionService):
        self._precision = precision_service
        self._min_rate = Decimal("0.00000001")

    def create(self, value: Decimal) -> Rate:
        normalized = self._precision.normalize_rate(value)

        if normalized <= 0:
            raise ValueError(f"Rate must be positive, got: {normalized}")

        if normalized < self._min_rate:
            normalized = self._min_rate

        return Rate(normalized)

    def from_string(self, value: str) -> Rate:
        return self.create(Decimal(value))

    def from_float(self, value: float) -> Rate:
        return self.create(Decimal(str(value)))
