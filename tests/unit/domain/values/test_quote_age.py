from datetime import datetime, timezone

import pytest

from converter.domain.values import QuoteAge, TimestampUTC


def test_quote_age_positive_and_checks():
    qa = QuoteAge(0)

    assert qa.is_fresh(10) is True
    assert qa.is_stale(0) is False

    with pytest.raises(ValueError):
        QuoteAge(-1)


def test_between_and_since():
    t1 = TimestampUTC(datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc))
    t2 = TimestampUTC(datetime(2025, 10, 2, 12, 0, 10, tzinfo=timezone.utc))
    qa = QuoteAge.between(t1, t2)
    qas = QuoteAge.since(t1)

    assert qa.seconds == 10.0
    assert qas.seconds >= 0