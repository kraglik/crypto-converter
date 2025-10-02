from converter.app.ports.outbound.quote_repository import QuoteWriter
from converter.domain.models import Quote
from converter.shared.config import get_settings
from converter.shared.logging import get_logger
from converter.shared.observability import get_metrics_registry

logger = get_logger(__name__)
settings = get_settings()


class CompositeQuoteWriter(QuoteWriter):
    def __init__(
        self,
        primary: QuoteWriter,
        secondary: QuoteWriter,
    ):
        self._primary = primary
        self._secondary = secondary

    async def save_batch(self, quotes: list[Quote]) -> None:
        await self._primary.save_batch(quotes)

        try:
            await self._secondary.save_batch(quotes)
        except Exception as e:
            logger.error(
                "secondary_writer_failed",
                error=str(e),
                quote_count=len(quotes),
                exc_info=True,
            )

            # There's a better way to structure metrics collection
            # Withoout abstraction leakage
            # But I don't have enough time to do that.
            if settings.ENABLE_METRICS:
                metrics = get_metrics_registry()
                metrics.quotes_stored_total.labels(storage="redis", status="error").inc(
                    len(quotes)
                )
