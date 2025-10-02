from abc import ABC, abstractmethod
from typing import Optional

from converter.domain.models import Quote
from converter.domain.values import Pair, TimestampUTC


class QuoteRepository(ABC):
    @abstractmethod
    async def get_latest(self, pair: Pair) -> Optional[Quote]:
        """
        Get the most recent quote for a given currrency pair, if it exists at all,
        w.r.t. the 'before' timestamp - if provided.
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_latest_before(
        self, pair: Pair, timestamp: TimestampUTC
    ) -> Optional[Quote]:
        """
        Get quote closest to specified timestamp from the left side
        (the most recent quote before the timestamp provided).
        """
        raise NotImplementedError()


class QuoteWriter(ABC):
    @abstractmethod
    async def save_batch(self, quotes: list[Quote]) -> None:
        raise NotImplementedError()
