import time
from typing import Callable

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from converter.adapters.outbound.persistence.sqlalchemy.mapper import SQLAlchemyMapper
from converter.adapters.outbound.persistence.sqlalchemy.models import QuoteModel
from converter.app.ports.outbound.quote_repository import QuoteWriter
from converter.domain.exceptions.quote import QuoteStorageError
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.shared.config import get_settings
from converter.shared.logging import get_logger
from converter.shared.observability import get_metrics_registry

logger = get_logger(__name__)
settings = get_settings()


class PostgresQuoteWriter(QuoteWriter):
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession],
        rate_factory: RateFactory,
    ):
        self._session_factory = session_factory
        self._mapper = SQLAlchemyMapper(rate_factory)

    async def save_batch(self, quotes: list[Quote]) -> None:
        if not quotes:
            return

        start_time = time.time()

        try:
            values = [self._mapper.quote_to_dict(q) for q in quotes]
            stmt = insert(QuoteModel).values(values)

            stmt = stmt.on_conflict_do_nothing(
                index_elements=["symbol", "quote_timestamp"]
            )

            async with self._session_factory() as session, session.begin():
                await session.execute(stmt)

            duration = time.time() - start_time

            logger.debug(
                "postgres_batch_saved",
                quote_count=len(quotes),
                duration_ms=round(duration * 1000, 2),
            )

            if settings.ENABLE_METRICS:
                metrics = get_metrics_registry()
                metrics.quotes_stored_total.labels(storage="postgres").inc(len(quotes))
                metrics.db_queries_total.labels(
                    operation="insert_batch", table="quotes"
                ).inc()
                metrics.db_query_duration_seconds.labels(
                    operation="insert_batch", table="quotes"
                ).observe(duration)

        except Exception as e:
            logger.error(
                "postgres_batch_save_failed",
                quote_count=len(quotes),
                error=str(e),
                exc_info=True,
            )
            raise QuoteStorageError(operation="save_batch", reason=str(e)) from e
