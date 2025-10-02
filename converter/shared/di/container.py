from decimal import ROUND_HALF_UP, Decimal

import redis.asyncio as redis
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from converter.adapters.inbound.consumer.quote_consumer import QuoteConsumer
from converter.adapters.outbound.external.binance.client import BinanceAPIClient
from converter.adapters.outbound.external.binance.rate_source import (
    BinanceStreamingRateSource,
)
from converter.adapters.outbound.persistence.redis.quote_repository import (
    RedisQuoteRepository,
)
from converter.adapters.outbound.persistence.redis.quote_writer import RedisQuoteWriter
from converter.adapters.outbound.persistence.repositories.composite_quote_repository import (
    CompositeQuoteRepository,
)
from converter.adapters.outbound.persistence.repositories.composite_quote_writer import (
    CompositeQuoteWriter,
)
from converter.adapters.outbound.persistence.sqlalchemy.quote_repository import (
    PostgresQuoteRepository,
)
from converter.adapters.outbound.persistence.sqlalchemy.quote_writer import (
    PostgresQuoteWriter,
)
from converter.app.commands.store_quotes import StoreQuotesCommandHandler
from converter.app.queries.get_conversion import GetConversionQueryHandler
from converter.domain.services import ConversionService
from converter.domain.services.factory import AmountFactory, RateFactory
from converter.domain.services.precision_service import (
    PrecisionPolicy,
    PrecisionService,
)
from converter.domain.services.quote_freshness_service import (
    FreshnessPolicy,
    QuoteFreshnessService,
)
from converter.shared.config import get_settings
from converter.shared.logging import get_logger
from converter.shared.utils.scheduler import FixedRateScheduler

logger = get_logger(__name__)


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    logger = providers.Singleton(get_logger, __name__)

    db_engine = providers.Singleton(
        create_async_engine,
        config.database_url,
        pool_size=config.db_pool_size,
        max_overflow=config.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
        future=True,
        echo=False,
    )

    db_session_factory = providers.Singleton(
        async_sessionmaker,
        bind=db_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    redis_client = providers.Singleton(
        redis.from_url,
        config.redis_url,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5,
        max_connections=50,
        health_check_interval=30,
        retry_on_timeout=True,
        retry_on_error=[ConnectionError, TimeoutError],
    )

    precision_policy = providers.Singleton(
        PrecisionPolicy,
        amount_precision=Decimal("0.00000001"),
        rate_precision=Decimal("0.00000001"),
        rounding_mode=ROUND_HALF_UP,
    )

    precision_service = providers.Singleton(
        PrecisionService,
        policy=precision_policy,
    )

    rate_factory = providers.Singleton(
        RateFactory,
        precision_service=precision_service,
    )

    amount_factory = providers.Singleton(
        AmountFactory,
        precision_service=precision_service,
    )

    freshness_policy = providers.Singleton(
        FreshnessPolicy,
        max_age_seconds=config.quote_max_age_seconds,
    )

    freshness_service = providers.Singleton(
        QuoteFreshnessService,
        policy=freshness_policy,
    )

    conversion_service = providers.Singleton(
        ConversionService,
        freshness_service=freshness_service,
    )

    binance_api_client = providers.Singleton(
        BinanceAPIClient,
        timeout=config.binance_api_timeout,
        max_connections=config.binance_max_connections,
        max_connections_per_host=config.binance_max_connections_per_host,
        enable_circuit_breaker=config.binance_enable_circuit_breaker,
        circuit_breaker_failure_threshold=config.binance_circuit_breaker_failure_threshold,
        circuit_breaker_recovery_timeout=config.binance_circuit_breaker_recovery_timeout,
    )

    scheduler = providers.Singleton(FixedRateScheduler)

    rate_source = providers.Singleton(
        BinanceStreamingRateSource,
        api_client=binance_api_client,
        rate_factory=rate_factory,
        rates_interval_seconds=config.fetch_interval_seconds,
        symbols_interval_seconds=config.symbol_refresh_interval_seconds,
        queue_maxsize=10,
        scheduler=scheduler,
    )

    redis_quote_repository = providers.Factory(
        RedisQuoteRepository,
        redis_client=redis_client,
        rate_factory=rate_factory,
    )

    redis_quote_writer = providers.Factory(
        RedisQuoteWriter,
        redis_client=redis_client,
        rate_factory=rate_factory,
        ttl_seconds=config.redis_quote_ttl_seconds,
    )

    postgres_quote_repository = providers.Factory(
        PostgresQuoteRepository,
        rate_factory=rate_factory,
        session_factory=db_session_factory,
    )

    postgres_quote_writer = providers.Factory(
        PostgresQuoteWriter,
        rate_factory=rate_factory,
        session_factory=db_session_factory,
    )

    composite_quote_repository = providers.Factory(
        CompositeQuoteRepository,
        primary=redis_quote_repository,
        fallback=postgres_quote_repository,
    )

    composite_quote_writer = providers.Factory(
        CompositeQuoteWriter,
        primary=postgres_quote_writer,
        secondary=redis_quote_writer,
    )

    conversion_query_handler = providers.Factory(
        GetConversionQueryHandler,
        quote_repository=composite_quote_repository,
        conversion_service=conversion_service,
    )

    store_quotes_command_handler = providers.Factory(
        StoreQuotesCommandHandler,
        quote_writer_factory=composite_quote_writer,
    )

    quote_consumer = providers.Singleton(
        QuoteConsumer,
        rate_source=rate_source,
        handler=store_quotes_command_handler,
    )


async def cleanup_resources(container: Container) -> None:
    logger.info("container_cleanup_starting")

    try:
        scheduler_instance = container.scheduler()
        await scheduler_instance.shutdown()
        logger.info("scheduler_shutdown_complete")
    except Exception as e:
        logger.warning("scheduler_shutdown_error", error=str(e))

    try:
        consumer_instance = container.quote_consumer()
        await consumer_instance.stop()
        logger.info("quote_consumer_shutdown_complete")
    except Exception as e:
        logger.warning("quote_consumer_shutdown_error", error=str(e))

    try:
        rate_source_instance = container.rate_source()
        await rate_source_instance.close()
        logger.info("rate_source_shutdown_complete")
    except Exception as e:
        logger.warning("rate_source_shutdown_error", error=str(e))

    try:
        binance_client = container.binance_api_client()
        await binance_client.close()
        logger.info("binance_client_closed")
    except Exception as e:
        logger.warning("binance_client_close_error", error=str(e))

    try:
        redis_instance = container.redis_client()
        await redis_instance.aclose()
        logger.info("redis_closed")
    except Exception as e:
        logger.warning("redis_close_error", error=str(e))

    try:
        engine_instance = container.db_engine()
        await engine_instance.dispose()
        logger.info("database_engine_disposed")
    except Exception as e:
        logger.warning("engine_dispose_error", error=str(e))

    logger.info("container_cleanup_complete")


def get_container(app_type: str = "api") -> Container:
    settings = get_settings()

    container = Container()

    redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"

    if app_type == "api":
        db_pool_size = 20
        db_max_overflow = 10
    else:
        db_pool_size = 5
        db_max_overflow = 5

    container.config.from_dict(
        {
            "database_url": str(settings.DATABASE_URL),
            "redis_url": redis_url,
            "db_pool_size": db_pool_size,
            "db_max_overflow": db_max_overflow,
            "redis_quote_ttl_seconds": settings.REDIS_QUOTE_TTL_SECONDS,
            "quote_max_age_seconds": settings.QUOTE_MAX_AGE_SECONDS,
            "fetch_interval_seconds": float(settings.FETCH_INTERVAL_SECONDS),
            "symbol_refresh_interval_seconds": float(
                settings.SYMBOL_FETCH_INTERVAL_SECONDS
            ),
            "binance_api_timeout": settings.BINANCE_API_TIMEOUT,
            "binance_max_connections": settings.BINANCE_MAX_CONNECTIONS,
            "binance_max_connections_per_host": settings.BINANCE_MAX_CONNECTIONS_PER_HOST,
            "binance_enable_circuit_breaker": settings.BINANCE_ENABLE_CIRCUIT_BREAKER,
            "binance_circuit_breaker_failure_threshold": settings.BINANCE_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            "binance_circuit_breaker_recovery_timeout": settings.BINANCE_CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
        }
    )

    logger.info("di_container_configured", app_type=app_type, db_pool_size=db_pool_size)

    return container
