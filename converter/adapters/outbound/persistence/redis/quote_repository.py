import json
from typing import Optional

import redis.asyncio as redis

from converter.app.ports.outbound.quote_repository import QuoteRepository
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.values import Pair, TimestampUTC
from converter.shared.config import get_settings
from converter.shared.logging import get_logger
from converter.shared.observability import get_metrics_registry

from .mapper import RedisMapper
from .models import RedisTicker

logger = get_logger(__name__)
settings = get_settings()


# Essentially an unreliable cache layer.
# It's good if it works, it's fine if it doesn't.
class RedisQuoteRepository(QuoteRepository):
    def __init__(
        self,
        redis_client: redis.Redis,
        rate_factory: RateFactory,
    ):
        self._redis = redis_client
        self._mapper = RedisMapper(rate_factory)

    async def get_latest(self, pair: Pair) -> Optional[Quote]:
        key = self._make_key(pair)

        try:
            data = await self._redis.get(key)

            if not data:
                logger.debug("redis_cache_miss", key=key)

                if settings.ENABLE_METRICS:
                    metrics = get_metrics_registry()
                    metrics.cache_misses_total.labels(cache_type="redis").inc()

                return None

            payload = json.loads(data)
            ticker = RedisTicker.from_dict(payload)
            quote = self._mapper.map_ticker_to_quote(ticker=ticker, pair=pair)

            logger.debug("redis_cache_hit", key=key)

            if settings.ENABLE_METRICS:
                metrics = get_metrics_registry()
                metrics.cache_hits_total.labels(cache_type="redis").inc()

            return quote

        except Exception as e:
            logger.warning("redis_get_failed", key=key, error=str(e))
            return None

    async def get_latest_before(
        self, pair: Pair, timestamp: TimestampUTC
    ) -> Optional[Quote]:
        """Historical queries are not supported by this repo"""
        logger.debug(
            "redis_historical_query_unsupported",
            pair=str(pair),
            timestamp=str(timestamp),
        )
        return None

    @staticmethod
    def _make_key(pair: Pair) -> str:
        return f"quote:latest:{pair}"
