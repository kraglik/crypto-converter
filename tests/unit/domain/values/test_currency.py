import pytest

from converter.domain.values import Currency


def test_currency_normalizes_to_uppercase_and_allows_underscore():
    c = Currency("bt_c1")
    assert c.code == "BT_C1"
    assert str(c) == "BT_C1"


def test_currency_invalid_empty():
    with pytest.raises(ValueError):
        Currency("")


def test_currency_invalid_chars():
    with pytest.raises(ValueError):
        Currency("BTC-USD")


def test_currency_length_bounds():
    Currency("A" * 20)  # ok
    with pytest.raises(ValueError):
        Currency("A" * 21)


def test_currency_equality_and_hash():
    a = Currency("btc")
    b = Currency("BTC")
    c = Currency("ETH")
    assert a == b
    assert a != c
    assert {a, b, c} == {Currency("BTC"), Currency("ETH")}
