from functools import lru_cache
from typing import Optional

from pydantic import Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    LOG_LEVEL: str = Field(
        default="INFO", description="Logging level [DEBUG, INFO, WARNING, ERROR]"
    )

    DATABASE_URL: PostgresDsn = Field(
        default="postgresql+asyncpg://converter_consumer:consumer_dev_pass@postgres/crypto_converter",
        description="PostgreSQL connection string for the db",
        examples=["postgresql+asyncpg://user:pass@host:port/db"],
    )

    REDIS_HOST: str = Field(
        default="redis",
        description="Redis host address",
    )

    REDIS_PORT: int = Field(
        default=6379,
        ge=1,
        le=65535,
        description="Redis port number",
    )

    API_HOST: str = Field(
        default="0.0.0.0", description="Host address to bind the API server to"
    )

    API_PORT: int = Field(
        default=8000, ge=1, le=65535, description="Port to run the API server on"
    )

    FETCH_INTERVAL_SECONDS: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Interval in seconds for fetching new quotes",
    )

    SYMBOL_FETCH_INTERVAL_SECONDS: int = Field(
        default=60,
        ge=60,
        le=300,
        description="Interval in seconds for fetching latest symbol list",
    )

    QUOTE_MAX_AGE_SECONDS: int = Field(
        default=60,
        ge=30,
        le=300,
        description="Maximum age of quotes before considered stale",
    )

    REDIS_QUOTE_TTL_SECONDS: int = Field(
        default=60, ge=30, description="TTL for quotes in Redis cache"
    )

    BINANCE_API_TIMEOUT: int = Field(
        default=10, ge=5, le=30, description="Timeout for Binance API requests"
    )

    BINANCE_MAX_CONNECTIONS: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of simultaneous connections to Binance API",
    )

    BINANCE_MAX_CONNECTIONS_PER_HOST: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of simultaneous connections to Binance API per single host",
    )

    BINANCE_ENABLE_CIRCUIT_BREAKER: bool = Field(
        default=True,
        description="Enable circuit breaker for Binance API",
    )

    BINANCE_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of failures before circuit breaker opens",
    )

    BINANCE_CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Seconds to wait before attempting to close circuit breaker",
    )

    ENABLE_METRICS: bool = Field(
        default=False,
        description="Should metrics collection be enabled?",
    )

    ENABLE_TRACING: bool = Field(
        default=False,
        description="Should tracing be enabled?",
    )

    JSON_LOGS: bool = Field(
        default=False,
        description="Should logs be in JSON format?",
    )

    OPEN_TELEMETRY_COLLECTOR_ENDPOINT: Optional[str] = Field(
        default=None, description="OpenTelemetry collector endpoint"
    )

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if value.upper() not in valid_levels:
            raise ValueError(
                f"Invalid LOG_LEVEL '{value}'. Must be one of {valid_levels}"
            )
        return value.upper()

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: PostgresDsn) -> PostgresDsn:
        if not str(value).startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use asyncpg driver (postgresql+asyncpg://...)"
            )
        return value

    @model_validator(mode="after")
    def validate_ttl_relationships(self) -> "Settings":
        if self.REDIS_QUOTE_TTL_SECONDS <= self.QUOTE_MAX_AGE_SECONDS:
            raise ValueError(
                f"REDIS_QUOTE_TTL_SECONDS ({self.REDIS_QUOTE_TTL_SECONDS}) "
                f"should be greater than QUOTE_MAX_AGE_SECONDS ({self.QUOTE_MAX_AGE_SECONDS})"
            )
        return self


@lru_cache()
def get_settings() -> Settings:
    from converter.shared.logging import get_logger

    logger = get_logger(__name__)

    try:
        settings = Settings()
        logger.info("Settings loaded successfully")
        return settings

    except Exception as e:
        logger.error(f"Failed to load settings: {e}", exc_info=True)
        raise
