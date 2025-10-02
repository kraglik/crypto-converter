import importlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from converter.app.queries.get_conversion import ConversionResult as AppConversionResult
from converter.domain.exceptions.conversion import (
    QuoteNotFoundError,
    QuoteTooOldError,
)
from converter.domain.values import (
    Amount,
    Currency,
    Pair,
    QuoteAge,
    Rate,
    TimestampUTC,
)


class MockRedis:
    async def ping(self):
        return True


class MockContainer:
    def redis_client(self):
        return MockRedis()

    async def cleanup_resources(self):
        pass


class MockHandler:
    def __init__(self, result=None, error: Optional[Exception] = None, capture_query: bool = False):
        self._result = result
        self._error = error
        self.capture_query = capture_query
        self.last_query = None

    async def handle(self, query):
        if self.capture_query:
            self.last_query = query
        if self._error is not None:
            raise self._error
        return self._result


def _app_with_overrides(monkeypatch, app_module, handler: MockHandler):
    from converter.shared import di as di_module
    monkeypatch.setattr(di_module, "get_container", lambda *args, **kwargs: MockContainer())

    app_mod = importlib.reload(app_module)
    app = app_mod.app

    from converter.adapters.inbound.api.dependencies.services import (
        get_amount_factory,
        get_conversion_query_handler,
    )
    from converter.domain.services.factory import AmountFactory
    from converter.domain.services.precision_service import PrecisionService

    app.dependency_overrides[get_conversion_query_handler] = lambda: handler
    app.dependency_overrides[get_amount_factory] = lambda: AmountFactory(PrecisionService())

    return app


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def test_convert_success(monkeypatch):
    import converter.adapters.inbound.api.app as app_module

    ts = TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc))
    app_result = AppConversionResult(
        amount=Amount(Decimal("50000")),
        original_amount=Amount(Decimal("2")),
        rate=Rate(Decimal("25000")),
        timestamp=ts,
    )
    handler = MockHandler(result=app_result)

    app = _app_with_overrides(monkeypatch, app_module, handler)

    with TestClient(app) as client:
        resp = client.get("/convert", params={"amount": "2", "from": "BTC", "to": "USDT"})
        assert resp.status_code == 200
        data = resp.json()

        assert data["amount"] == "50000"
        assert data["rate"] == "25000"
        returned_ts = _parse_ts(data["timestamp"])
        assert returned_ts == ts.value


def test_convert_historical_timestamp_passed_to_handler(monkeypatch):
    import converter.adapters.inbound.api.app as app_module

    ts = TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc))
    app_result = AppConversionResult(
        amount=Amount(Decimal("1")),
        original_amount=Amount(Decimal("1")),
        rate=Rate(Decimal("1")),
        timestamp=ts,
    )
    handler = MockHandler(result=app_result, capture_query=True)

    app = _app_with_overrides(monkeypatch, app_module, handler)

    hist = datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    with TestClient(app) as client:
        resp = client.get("/convert", params={"amount": "1", "from": "BTC", "to": "USDT", "timestamp": hist})
        assert resp.status_code == 200
        assert handler.last_query is not None
        assert handler.last_query.at_timestamp is not None
        assert handler.last_query.at_timestamp.value == datetime(2025, 10, 2, 12, 0, 0, tzinfo=timezone.utc)


def test_convert_quote_not_found(monkeypatch):
    import converter.adapters.inbound.api.app as app_module

    pair = Pair(Currency("BTC"), Currency("USDT"))
    handler = MockHandler(error=QuoteNotFoundError(pair))

    app = _app_with_overrides(monkeypatch, app_module, handler)

    with TestClient(app) as client:
        resp = client.get("/convert", params={"amount": "1", "from": "BTC", "to": "USDT"})
        assert resp.status_code == 404
        data = resp.json()
        assert "No quote found for pair BTCUSDT" in data["detail"]


def test_convert_quote_too_old(monkeypatch):
    import converter.adapters.inbound.api.app as app_module

    pair = Pair(Currency("BTC"), Currency("USDT"))
    age = QuoteAge(61.0)
    ref = TimestampUTC(datetime(2025, 10, 2, 0, 1, 1, tzinfo=timezone.utc))
    handler = MockHandler(error=QuoteTooOldError(pair=pair, age=age, max_age_seconds=60, reference_time=ref))

    app = _app_with_overrides(monkeypatch, app_module, handler)

    with TestClient(app) as client:
        resp = client.get("/convert", params={"amount": "1", "from": "BTC", "to": "USDT"})
        assert resp.status_code == 422
        data = resp.json()
        assert "too old" in data["detail"]


def test_convert_value_error_returns_400(monkeypatch):
    import converter.adapters.inbound.api.app as app_module

    handler = MockHandler(error=ValueError("Bad conversion parameters"))
    app = _app_with_overrides(monkeypatch, app_module, handler)

    with TestClient(app) as client:
        resp = client.get("/convert", params={"amount": "1", "from": "BTC", "to": "USDT"})
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Bad conversion parameters"


def test_convert_internal_error_returns_500(monkeypatch):
    import converter.adapters.inbound.api.app as app_module

    handler = MockHandler(error=RuntimeError("Boom"))
    app = _app_with_overrides(monkeypatch, app_module, handler)

    with TestClient(app) as client:
        resp = client.get("/convert", params={"amount": "1", "from": "BTC", "to": "USDT"})
        assert resp.status_code == 500
        assert resp.json()["detail"] == "An unexpected error occurred during conversion"


@pytest.mark.parametrize(
    "params",
    [
        {"amount": "0", "from": "BTC", "to": "USDT"},
        {"amount": "-1", "from": "BTC", "to": "USDT"},
        {"amount": "1", "from": "BT-C", "to": "USDT"},
        {"amount": "1", "from": "BTC", "to": "BT-C"},
        {"amount": "1", "from": "BTC", "to": "BTC"},
    ],
)
def test_convert_validation_errors_422(monkeypatch, params):
    import converter.adapters.inbound.api.app as app_module

    ts = TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc))
    app_result = AppConversionResult(
        amount=Amount(Decimal("1")),
        original_amount=Amount(Decimal("1")),
        rate=Rate(Decimal("1")),
        timestamp=ts,
    )
    handler = MockHandler(result=app_result)

    app = _app_with_overrides(monkeypatch, app_module, handler)

    with TestClient(app) as client:
        resp = client.get("/convert", params=params)
        assert resp.status_code == 422


def test_convert_timestamp_future_422(monkeypatch):
    import converter.adapters.inbound.api.app as app_module

    app_result = AppConversionResult(
        amount=Amount(Decimal("1")),
        original_amount=Amount(Decimal("1")),
        rate=Rate(Decimal("1")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc)),
    )
    handler = MockHandler(result=app_result)
    app = _app_with_overrides(monkeypatch, app_module, handler)

    future = datetime.now(timezone.utc) + timedelta(minutes=1)
    with TestClient(app) as client:
        resp = client.get(
            "/convert",
            params={
                "amount": "1",
                "from": "BTC",
                "to": "USDT",
                "timestamp": future.isoformat(),
            },
        )
        assert resp.status_code == 422
        assert "future" in resp.json()["detail"]


def test_convert_timestamp_too_old_422(monkeypatch):
    import converter.adapters.inbound.api.app as app_module

    handler = MockHandler(result=AppConversionResult(
        amount=Amount(Decimal("1")),
        original_amount=Amount(Decimal("1")),
        rate=Rate(Decimal("1")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc)),
    ))
    app = _app_with_overrides(monkeypatch, app_module, handler)

    old = datetime.now(timezone.utc) - timedelta(days=8)
    with TestClient(app) as client:
        resp = client.get(
            "/convert",
            params={
                "amount": "1",
                "from": "BTC",
                "to": "USDT",
                "timestamp": old.isoformat(),
            },
        )
        assert resp.status_code == 422
        assert "older than 7 days" in resp.json()["detail"]
