import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import AsyncIterator

import pytest
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from converter.shared.config import get_settings


@pytest.fixture(scope="session")
def postgres_container() -> PostgresContainer:
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope="session")
def postgres_async_url(postgres_container: PostgresContainer) -> str:
    host = postgres_container.get_container_host_ip()
    port = int(postgres_container.get_exposed_port(5432))
    db = postgres_container.dbname
    user = postgres_container.username
    password = postgres_container.password
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture(scope="session")
def redis_container() -> RedisContainer:
    container = RedisContainer("redis:8-alpine")
    container.start()
    try:
        yield container
    finally:
        container.stop()




async def _init_partitioned_schema(engine: AsyncEngine) -> None:
    def day_start(d: date) -> datetime:
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)

    today = datetime.now(timezone.utc).date()
    tomorrow = today + timedelta(days=1)
    day_after = tomorrow + timedelta(days=1)

    start_today = day_start(today).isoformat()
    start_tomorrow = day_start(tomorrow).isoformat()
    start_day_after = day_start(day_after).isoformat()

    part_today = f"quotes_{today.strftime('%Y%m%d')}"
    part_tomorrow = f"quotes_{tomorrow.strftime('%Y%m%d')}"

    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS public.quotes (
                    symbol            VARCHAR(40) NOT NULL,
                    base_currency     VARCHAR(20) NOT NULL,
                    quote_currency    VARCHAR(20) NOT NULL,
                    rate              NUMERIC(36, 8) NOT NULL,
                    quote_timestamp   TIMESTAMPTZ NOT NULL,
                    created_at        TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (symbol, quote_timestamp)
                ) PARTITION BY RANGE (quote_timestamp)
                """
            )
        )

        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_quotes_symbol_timestamp "
                "ON public.quotes (symbol, quote_timestamp DESC)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_quotes_timestamp "
                "ON public.quotes (quote_timestamp DESC)"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_quotes_base_quote_timestamp "
                "ON public.quotes (base_currency, quote_currency, quote_timestamp DESC)"
            )
        )

        await conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS public.{part_today}
                PARTITION OF public.quotes
                FOR VALUES FROM ('{start_today}') TO ('{start_tomorrow}')
                """
            )
        )

        await conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS public.{part_tomorrow}
                PARTITION OF public.quotes
                FOR VALUES FROM ('{start_tomorrow}') TO ('{start_day_after}')
                """
            )
        )


@pytest.fixture(scope="function")
async def postgres_engine(postgres_async_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        postgres_async_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        future=True,
        echo=False,
    )

    await _init_partitioned_schema(engine)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(scope="function")
def session_factory(postgres_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=postgres_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest.fixture(scope="function")
async def redis_client(redis_container: RedisContainer) -> AsyncIterator[aioredis.Redis]:
    host = redis_container.get_container_host_ip()
    port = int(redis_container.get_exposed_port(6379))
    client = aioredis.from_url(f"redis://{host}:{port}/0", decode_responses=False)
    try:
        await client.ping()
        yield client
    finally:
        await client.aclose()


@pytest.fixture(scope="function")
def env_infra(monkeypatch, postgres_async_url: str, redis_container: RedisContainer):
    host = redis_container.get_container_host_ip()
    port = int(redis_container.get_exposed_port(6379))

    monkeypatch.setenv("DATABASE_URL", postgres_async_url)
    monkeypatch.setenv("REDIS_HOST", host)
    monkeypatch.setenv("REDIS_PORT", str(port))
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("JSON_LOGS", "false")
    monkeypatch.setenv("ENABLE_METRICS", "false")
    monkeypatch.setenv("ENABLE_TRACING", "false")
    monkeypatch.setenv("QUOTE_MAX_AGE_SECONDS", "60")
    monkeypatch.setenv("REDIS_QUOTE_TTL_SECONDS", "120")

    get_settings.cache_clear()