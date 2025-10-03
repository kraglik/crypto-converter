from datetime import datetime, timezone
from decimal import Decimal

import pytest
from converter.adapters.outbound.persistence.redis.models import RedisTicker


def test_redis_ticker_happy_path_and_roundtrip():
    # Given
    t = RedisTicker(
        symbol="BTCUSDT",
        rate=Decimal("25000.5"),
        timestamp=datetime(2025, 10, 2, 0, 0, tzinfo=timezone.utc),
    )

    # When
    d = t.to_dict()
    t2 = RedisTicker.from_dict(d)

    # Then
    assert t2.symbol == "BTCUSDT"
    assert t2.rate == Decimal("25000.5")
    assert t2.timestamp == t.timestamp


def test_redis_ticker_validation():
    with pytest.raises(ValueError):
        RedisTicker(symbol="", rate=Decimal("1"), timestamp=datetime.now(timezone.utc))
    with pytest.raises(ValueError):
        RedisTicker(
            symbol="btcusdt", rate=Decimal("1"), timestamp=datetime.now(timezone.utc)
        )
    with pytest.raises(ValueError):
        RedisTicker(
            symbol="BTCUSDT", rate=Decimal("-1"), timestamp=datetime.now(timezone.utc)
        )


def test_redis_ticker_from_dict_errors():
    with pytest.raises(ValueError):
        RedisTicker.from_dict(
            {"symbol": "BTCUSDT", "timestamp": "2025-10-02T00:00:00+00:00"}
        )
    with pytest.raises(ValueError):
        RedisTicker.from_dict(
            {"symbol": "BTCUSDT", "rate": "x", "timestamp": "2025-10-02T00:00:00+00:00"}
        )
