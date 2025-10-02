from decimal import Decimal

from converter.domain.services.precision_service import (
    PrecisionPolicy,
    PrecisionService,
)


def test_normalize_amount_rounds_to_8_decimals_half_up():
    svc = PrecisionService(PrecisionPolicy())

    v = Decimal("1.234567895")
    v2 = Decimal("1.234567894")

    assert svc.normalize_amount(v) == Decimal("1.23456790")
    assert svc.normalize_amount(v2) == Decimal("1.23456789")


def test_normalize_rate_rounds_to_8_decimals_half_up():
    svc = PrecisionService(PrecisionPolicy())

    assert svc.normalize_rate(Decimal("0.123456785")) == Decimal("0.12345679")
    assert svc.normalize_rate(Decimal("0.123456784")) == Decimal("0.12345678")


def test_validate_precision_checks_expected_quantization():
    svc = PrecisionService(PrecisionPolicy())
    v = Decimal("1.23456789")

    expected_precision = Decimal("0.00000001")
    mismatching_precision = Decimal("1.234567891")

    assert svc.validate_precision(v, expected_precision) is True
    assert svc.validate_precision(mismatching_precision, expected_precision) is False