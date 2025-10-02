from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

from converter.domain.models import Quote


@dataclass(frozen=True)
class RateBatch:
    quotes: list[Quote]

    def __len__(self) -> int:
        return len(self.quotes)

    def __bool__(self) -> bool:
        return len(self.quotes) > 0


class RateSource(ABC):
    @abstractmethod
    def stream(self) -> AsyncIterator[RateBatch]:
        """
        Stream rate updates.
        """
        raise NotImplementedError()

    @abstractmethod
    async def close(self) -> None:
        """
        Close the rate source and cleanup resources.
        """
        raise NotImplementedError()
