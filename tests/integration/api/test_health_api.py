import importlib

import converter.adapters.inbound.api.app as app_module
from converter.adapters.inbound.api.dependencies.db import get_db_session
from converter.adapters.inbound.api.dependencies.services import get_redis_client
from fastapi.testclient import TestClient


class MockDBSession:
    def __init__(self, fail: bool = False):
        self.fail = fail

    async def execute(self, stmt):
        if self.fail:
            raise Exception("db error")

        class R:
            pass

        return R()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class MockRedis:
    def __init__(self, fail: bool = False):
        self.fail = fail

    async def ping(self):
        if self.fail:
            raise Exception("redis error")
        return True


class MockContainer:
    def redis_client(self):
        return MockRedis(fail=False)

    async def cleanup_resources(self):
        pass


def _build_app(monkeypatch, db_fail: bool = False, redis_fail: bool = False):
    from converter.shared import di as di_module

    monkeypatch.setattr(
        di_module, "get_container", lambda *args, **kwargs: MockContainer()
    )

    app = importlib.reload(app_module).app

    async def override_db_session():
        yield MockDBSession(fail=db_fail)

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_redis_client] = lambda: MockRedis(fail=redis_fail)

    return app


def test_health_ok(monkeypatch):
    app = _build_app(monkeypatch, db_fail=False, redis_fail=False)
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["checks"]["postgres"]["status"] == "healthy"
        assert data["checks"]["redis"]["status"] == "healthy"


def test_health_redis_unhealthy(monkeypatch):
    app = _build_app(monkeypatch, db_fail=False, redis_fail=True)
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["postgres"]["status"] == "healthy"
        assert data["checks"]["redis"]["status"] == "unhealthy"
        assert "error" in data["checks"]["redis"]


def test_health_db_unhealthy(monkeypatch):
    app = _build_app(monkeypatch, db_fail=True, redis_fail=False)
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["postgres"]["status"] == "unhealthy"
        assert "error" in data["checks"]["postgres"]
        assert data["checks"]["redis"]["status"] == "healthy"


def test_health_both_unhealthy(monkeypatch):
    app = _build_app(monkeypatch, db_fail=True, redis_fail=True)
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["postgres"]["status"] == "unhealthy"
        assert data["checks"]["redis"]["status"] == "unhealthy"
