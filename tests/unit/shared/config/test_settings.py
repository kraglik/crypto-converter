import pytest

from converter.shared.config import get_settings


def _reset_settings_cache():
    get_settings.cache_clear()


def test_settings_validate_log_level_and_db_url(monkeypatch):
    # Given
    _reset_settings_cache()
    monkeypatch.setenv("JSON_LOGS", "false")
    monkeypatch.setenv("REDIS_QUOTE_TTL_SECONDS", "120")
    monkeypatch.setenv("QUOTE_MAX_AGE_SECONDS", "60")

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")

    # When
    s = get_settings()

    # Then
    assert s.LOG_LEVEL == "DEBUG"
    assert str(s.DATABASE_URL).startswith("postgresql+asyncpg://")


def test_settings_rejects_sync_db_driver(monkeypatch):
    # Given
    _reset_settings_cache()
    monkeypatch.setenv("JSON_LOGS", "false")
    monkeypatch.setenv("REDIS_QUOTE_TTL_SECONDS", "120")
    monkeypatch.setenv("QUOTE_MAX_AGE_SECONDS", "60")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")

    # When & Then
    with pytest.raises(Exception):
        get_settings()


def test_settings_ttl_must_be_greater_than_max_age(monkeypatch):
    # Given
    _reset_settings_cache()
    monkeypatch.setenv("JSON_LOGS", "false")
    monkeypatch.setenv("QUOTE_MAX_AGE_SECONDS", "60")
    monkeypatch.setenv("REDIS_QUOTE_TTL_SECONDS", "60")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/db")

    # When & Then
    with pytest.raises(Exception):
        get_settings()
