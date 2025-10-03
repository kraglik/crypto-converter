from datetime import datetime, timezone
from decimal import Decimal

from converter.domain.models import Quote
from converter.domain.values import Amount, Currency, Pair, Rate, TimestampUTC


def _make_quote():
    pair = Pair(Currency("BTC"), Currency("USDT"))
    rate = Rate(Decimal("25000"))
    ts = TimestampUTC(datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc))

    return Quote(pair=pair, rate=rate, timestamp=ts)


def test_quote_convert_and_age():
    q = _make_quote()
    amt = Amount(Decimal("2"))
    converted = q.convert(amt)

    ref = TimestampUTC(datetime(2025, 10, 2, 12, 1, 0, tzinfo=timezone.utc))
    age = q.age(reference_time=ref)

    assert age.seconds == 60.0
    assert converted.value == Decimal("50000")


def test_quote_str_contains_key_parts():
    q = _make_quote()
    s = str(q)

    assert "BTCUSDT" in s
    assert "rate=25000" in s
    assert "2025-10-02T12:00:00+00:00" in s
