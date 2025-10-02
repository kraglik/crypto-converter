from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class PrecisionPolicy:
    """Policy defining precision requirements for different value types."""

    amount_precision: Decimal = Decimal("0.00000001")
    rate_precision: Decimal = Decimal("0.00000001")
    rounding_mode: str = ROUND_HALF_UP


class PrecisionService:
    """
    Domain service for handling numeric precision.
    """

    def __init__(self, policy: PrecisionPolicy = None):
        self._policy = policy or PrecisionPolicy()

    def normalize_amount(self, value: Decimal) -> Decimal:
        """
        Normalize amount values to standard precision.

        :param value: Decimal value
        :return: Normalized decimal with proper precision
        """
        return value.quantize(
            self._policy.amount_precision, rounding=self._policy.rounding_mode
        )

    def normalize_rate(self, value: Decimal) -> Decimal:
        """
        Normalize rate values to standard precision.

        :param value: Decimal value
        :return: Normalized decimal with required precision
        """
        return value.quantize(
            self._policy.rate_precision, rounding=self._policy.rounding_mode
        )

    def validate_precision(self, value: Decimal, expected: Decimal) -> bool:
        """
        Check if value has expected precision.

        :param value: Value to check
        :param expected: Expected precision (e.g., Decimal('0.01'))

        :return: bool(does precision match our expectations?)
        """
        return value == value.quantize(expected, rounding=self._policy.rounding_mode)
