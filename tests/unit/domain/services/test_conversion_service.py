from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import freezegun
import pytest

from converter.domain.exceptions.conversion import QuoteTooOldError
from converter.domain.models import Quote
from converter.domain.services.conversion_service import ConversionService
from converter.domain.services.quote_freshness_service import (
    FreshnessPolicy,
    QuoteFreshnessService,
)
from converter.domain.values import Amount, Currency, Pair, Rate, TimestampUTC


def _quote(rate: str = "100.0", at: Optional[datetime] = None) -> Quote:
    pair = Pair(Currency("BTC"), Currency("USDT"))
    r = Rate(Decimal(rate))
    ts = TimestampUTC(at or datetime(2025, 10, 2, 12, 12, 0, 0, tzinfo=timezone.utc))

    return Quote(pair=pair, rate=r, timestamp=ts)


@freezegun.freeze_time(datetime(2025, 10, 2, 12, 13, 0, 0, tzinfo=timezone.utc))
def test_convert_success_returns_conversion_result_fields():
    freshness = QuoteFreshnessService(FreshnessPolicy(max_age_seconds=120))
    svc = ConversionService(freshness_service=freshness)

    q = _quote(rate="25000")
    amount = Amount(Decimal("2"))
    ref = None
    result = svc.convert(amount, q, reference_time=ref)

    assert result.original_amount == amount
    assert result.pair == q.pair
    assert result.rate.value == Decimal("25000")
    assert result.timestamp == q.timestamp
    assert result.converted_amount.value == Decimal("50000")


def test_convert_raises_when_quote_stale():
    freshness = QuoteFreshnessService(FreshnessPolicy(max_age_seconds=60))
    svc = ConversionService(freshness_service=freshness)

    base = datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc)
    q = _quote(rate="1.0", at=base)
    ref = TimestampUTC(base + timedelta(seconds=120))

    with pytest.raises(QuoteTooOldError):
        svc.convert(Amount(Decimal("1.0")), q, reference_time=ref)