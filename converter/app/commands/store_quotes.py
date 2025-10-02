from dataclasses import dataclass

from converter.app.ports.outbound.quote_repository import QuoteWriter
from converter.domain.models import Quote
from converter.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class StoreQuotesCommand:
    quotes: list[Quote]


@dataclass(frozen=True)
class StoreQuotesResult:
    total_received: int


class StoreQuotesCommandHandler:
    def __init__(
        self,
        quote_writer_factory: QuoteWriter,
    ):
        self._writer_factory = quote_writer_factory

    async def handle(self, command: StoreQuotesCommand) -> StoreQuotesResult:
        total_received = len(command.quotes)
        quotes = command.quotes

        writer = self._writer_factory
        await writer.save_batch(quotes)

        logger.info("quotes_stored", quote_count=total_received)

        return StoreQuotesResult(
            total_received=total_received,
        )
