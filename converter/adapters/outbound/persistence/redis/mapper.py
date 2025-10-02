from converter.adapters.outbound.persistence.redis.models import RedisTicker
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.values import Pair, TimestampUTC


class RedisMapper:
    def __init__(self, rate_factory: RateFactory) -> None:
        self._rate_factory = rate_factory

    def map_ticker_to_quote(self, ticker: RedisTicker, pair: Pair) -> Quote:
        timestamp = TimestampUTC(ticker.timestamp)
        rate = self._rate_factory.create(ticker.rate)

        return Quote(
            timestamp=timestamp,
            rate=rate,
            pair=pair,
        )

    @staticmethod
    def map_quote_to_ticker(quote: Quote) -> RedisTicker:
        return RedisTicker(
            timestamp=quote.timestamp.value,
            rate=quote.rate.value,
            symbol=quote.pair.code(),
        )
