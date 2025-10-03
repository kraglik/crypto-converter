from decimal import Decimal

import pytest
from converter.domain.values import Amount


def test_amount_creation_positive_and_zero():
    assert Amount(Decimal("0")).value == Decimal("0")
    assert Amount(Decimal("1.23")).value == Decimal("1.23")


def test_amount_negative_raises():
    with pytest.raises(ValueError):
        Amount(Decimal("-0.0001"))


def test_amount_multiplication_returns_amount():
    amt = Amount(Decimal("2"))
    result = amt * Decimal("3.5")
    assert isinstance(result, Amount)
    assert result.value == Decimal("7.0")


def test_amount_is_zero():
    assert Amount(Decimal("0")).is_zero()
    assert not Amount(Decimal("0.00000001")).is_zero()


def test_amount_str():
    assert str(Amount(Decimal("1.234"))) == "1.234"
