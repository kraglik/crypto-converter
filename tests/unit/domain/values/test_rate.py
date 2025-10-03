from decimal import Decimal

import pytest
from converter.domain.values import Amount, Rate


def test_rate_positive_required():
    Rate(Decimal("0.00000001"))

    with pytest.raises(ValueError):
        Rate(Decimal("0"))

    with pytest.raises(ValueError):
        Rate(Decimal("-1"))


def test_rate_apply_to_amount():
    # Given
    r = Rate(Decimal("2.5"))
    amt = Amount(Decimal("4"))

    # When
    value = r.apply_to(amt).value

    # Then
    assert value == Decimal("10.0")


def test_rate_inverse():
    # Given
    r = Rate(Decimal("2"))

    # When
    inv = r.inverse()

    # Then
    assert isinstance(inv, Rate)
    assert inv.value == Decimal("0.5")
