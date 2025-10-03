import os

import pytest


@pytest.fixture(autouse=True)
def test_settings(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("JSON_LOGS", "false")
    monkeypatch.setenv("ENABLE_METRICS", "false")
    monkeypatch.setenv("ENABLE_TRACING", "false")
    monkeypatch.setenv(
        "DATABASE_URL",
        os.getenv(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://converter_consumer:consumer_dev_pass@postgres/crypto_converter",
        ),
    )
    monkeypatch.setenv("REDIS_HOST", os.getenv("TEST_REDIS_HOST", "redis"))
    monkeypatch.setenv("REDIS_PORT", os.getenv("TEST_REDIS_PORT", "6379"))
    monkeypatch.setenv("FETCH_INTERVAL_SECONDS", "30")
    monkeypatch.setenv("SYMBOL_FETCH_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("QUOTE_MAX_AGE_SECONDS", "60")
    monkeypatch.setenv("REDIS_QUOTE_TTL_SECONDS", "120")

    from converter.shared.config import get_settings

    get_settings.cache_clear()
