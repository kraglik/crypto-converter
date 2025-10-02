from typing import Optional

from converter.app.ports.outbound.quote_repository import QuoteRepository
from converter.domain.models import Quote
from converter.domain.values import Pair, TimestampUTC


class CompositeQuoteRepository(QuoteRepository):
    def __init__(self, primary: QuoteRepository, fallback: QuoteRepository):
        self._primary = primary
        self._fallback = fallback

    async def get_latest(self, pair: Pair) -> Optional[Quote]:
        quote = await self._primary.get_latest(pair)

        if quote:
            return quote

        return await self._fallback.get_latest(pair)

    async def get_latest_before(
        self, pair: Pair, timestamp: TimestampUTC
    ) -> Optional[Quote]:
        return await self._fallback.get_latest_before(pair, timestamp)
