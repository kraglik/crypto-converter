import pytest

from converter.domain.values import Currency, Pair


def test_pair_creation_and_str_code_inverse():
    # Given
    base = Currency("BTC")
    quote = Currency("USDT")

    # When
    p = Pair(base, quote)
    inv = p.inverse()

    # Then
    assert str(p) == "BTCUSDT"
    assert p.code() == "BTCUSDT"
    assert str(inv) == "USDTBTC"
    assert inv.base == quote and inv.quote == base


def test_pair_same_currency_raises():
    # Given
    c = Currency("BTC")

    # When & Then
    with pytest.raises(ValueError):
        Pair(c, c)
