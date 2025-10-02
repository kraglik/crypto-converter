from datetime import datetime, timedelta, timezone

from converter.domain.values import TimestampUTC


def test_timestamp_normalizes_naive_to_utc():
    naive = datetime(2025, 10, 2, 12, 0, 0)
    t = TimestampUTC(naive)

    assert t.value.tzinfo == timezone.utc
    assert t.value == datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc)


def test_timestamp_converts_tz_aware_to_utc():
    plus2 = timezone(timedelta(hours=2))
    aware = datetime(2025, 10, 2, 12, 0, 0, tzinfo=plus2)
    t = TimestampUTC(aware)

    assert t.value == datetime(2025, 10, 2, 10, 0, 0, tzinfo=timezone.utc)


def test_age_seconds_and_older_than():
    base = TimestampUTC(datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc))
    ref = TimestampUTC(datetime(2025, 10, 2, 12, 1, 30, tzinfo=timezone.utc))

    assert base.age_seconds(reference=ref) == 90.0
    assert base.is_older_than_seconds(60, reference=ref) is True
    assert base.is_older_than_seconds(120, reference=ref) is False


def test_from_helpers_and_str():
    ts = TimestampUTC.from_timestamp(1700000000.0)  # UTC
    assert ts.value.tzinfo == timezone.utc

    iso = "2025-10-02T00:00:00+00:00"
    ts2 = TimestampUTC.from_iso_string(iso)

    assert ts2.value == datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc)

    assert isinstance(str(ts2), str) and "2025-10-02T00:00:00+00:00" in str(ts2)
