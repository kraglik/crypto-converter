import time
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from converter.app.ports.outbound.quote_repository import QuoteRepository
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.values import Pair, TimestampUTC
from converter.shared.config import get_settings
from converter.shared.logging import get_logger
from converter.shared.observability import get_metrics_registry

from .mapper import SQLAlchemyMapper
from .models import QuoteModel

logger = get_logger(__name__)
settings = get_settings()


class PostgresQuoteRepository(QuoteRepository):
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        rate_factory: RateFactory,
    ):
        self._session_factory = session_factory
        self._mapper = SQLAlchemyMapper(rate_factory)

    async def get_latest(self, pair: Pair) -> Optional[Quote]:
        start_time = time.time()

        async with self._session_factory() as session:
            stmt = (
                select(QuoteModel)
                .where(QuoteModel.symbol == str(pair))
                .order_by(QuoteModel.quote_timestamp.desc())
                .limit(1)
            )

            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

        duration = time.time() - start_time

        logger.debug(
            "postgres_query",
            operation="get_latest",
            pair=str(pair),
            found=model is not None,
            duration_ms=round(duration * 1000, 2),
        )

        if settings.ENABLE_METRICS:
            metrics = get_metrics_registry()
            metrics.db_queries_total.labels(
                operation="get_latest", table="quotes"
            ).inc()
            metrics.db_query_duration_seconds.labels(
                operation="get_latest", table="quotes"
            ).observe(duration)

        return self._mapper.db_model_to_quote(model) if model else None

    async def get_latest_before(
        self, pair: Pair, timestamp: TimestampUTC
    ) -> Optional[Quote]:
        start_time = time.time()

        async with self._session_factory() as session:
            stmt = (
                select(QuoteModel)
                .where(
                    QuoteModel.symbol == str(pair),
                    QuoteModel.quote_timestamp <= timestamp.value,
                )
                .order_by(QuoteModel.quote_timestamp.desc())
                .limit(1)
            )

            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

        duration = time.time() - start_time

        logger.debug(
            "postgres_query",
            operation="get_latest_before",
            pair=str(pair),
            timestamp=str(timestamp),
            found=model is not None,
            duration_ms=round(duration * 1000, 2),
        )

        if settings.ENABLE_METRICS:
            metrics = get_metrics_registry()
            metrics.db_queries_total.labels(
                operation="get_latest_before", table="quotes"
            ).inc()
            metrics.db_query_duration_seconds.labels(
                operation="get_latest_before", table="quotes"
            ).observe(duration)

        return self._mapper.db_model_to_quote(model) if model else None
