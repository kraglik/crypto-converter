from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from converter.domain.exceptions.conversion import QuoteTooOldError
from converter.domain.models import Quote
from converter.domain.services.quote_freshness_service import (
    FreshnessPolicy,
    QuoteFreshnessService,
)
from converter.domain.values import Currency, Pair, Rate, TimestampUTC


def _quote_at(dt: datetime) -> Quote:
    pair = Pair(Currency("BTC"), Currency("USDT"))
    rate = Rate(Decimal("100.0"))
    ts = TimestampUTC(dt)

    return Quote(pair=pair, rate=rate, timestamp=ts)


def test_validate_freshness_allows_fresh_with_reference():
    policy = FreshnessPolicy(max_age_seconds=60)
    svc = QuoteFreshnessService(policy)

    t0 = datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
    quote = _quote_at(t0)
    ref = TimestampUTC(t0 + timedelta(seconds=30))

    svc.validate_freshness(quote, ref)


def test_validate_freshness_raises_when_stale():
    policy = FreshnessPolicy(max_age_seconds=60)
    svc = QuoteFreshnessService(policy)

    t0 = datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
    quote = _quote_at(t0)
    ref = TimestampUTC(t0 + timedelta(seconds=61))

    with pytest.raises(QuoteTooOldError):
        svc.validate_freshness(quote, ref)


def test_is_fresh_and_filter_fresh_quotes():
    base = datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc)

    policy = FreshnessPolicy(max_age_seconds=60)
    svc = QuoteFreshnessService(policy)

    fresh_q = _quote_at(base)
    stale_q = _quote_at(base - timedelta(seconds=60))

    ref = TimestampUTC(base + timedelta(seconds=30))
    filtered = svc.filter_fresh_quotes([fresh_q, stale_q], reference_time=ref)

    assert svc.is_fresh(fresh_q, TimestampUTC(base + timedelta(seconds=30))) is True
    assert svc.is_fresh(stale_q, ref) is False
    assert filtered == [fresh_q]
