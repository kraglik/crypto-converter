import json

import redis.asyncio as redis

from converter.app.ports.outbound.quote_repository import QuoteWriter
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.shared.config import get_settings
from converter.shared.logging import get_logger
from converter.shared.observability import get_metrics_registry

from .mapper import RedisMapper

logger = get_logger(__name__)
settings = get_settings()


class RedisQuoteWriter(QuoteWriter):
    def __init__(
        self,
        redis_client: redis.Redis,
        rate_factory: RateFactory,
        ttl_seconds: int = 60,
    ):
        self._redis = redis_client
        self._mapper = RedisMapper(rate_factory)
        self._ttl = ttl_seconds

    async def save_batch(self, quotes: list[Quote]) -> None:
        if not quotes:
            """
            ———————————No quotes?———————————
            ⠀⣞⢽⢪⢣⢣⢣⢫⡺⡵⣝⡮⣗⢷⢽⢽⢽⣮⡷⡽⣜⣜⢮⢺⣜⢷⢽⢝⡽⣝
            ⠸⡸⠜⠕⠕⠁⢁⢇⢏⢽⢺⣪⡳⡝⣎⣏⢯⢞⡿⣟⣷⣳⢯⡷⣽⢽⢯⣳⣫⠇
            ⠀⠀⢀⢀⢄⢬⢪⡪⡎⣆⡈⠚⠜⠕⠇⠗⠝⢕⢯⢫⣞⣯⣿⣻⡽⣏⢗⣗⠏⠀
            ⠀⠪⡪⡪⣪⢪⢺⢸⢢⢓⢆⢤⢀⠀⠀⠀⠀⠈⢊⢞⡾⣿⡯⣏⢮⠷⠁⠀⠀
            ⠀⠀⠀⠈⠊⠆⡃⠕⢕⢇⢇⢇⢇⢇⢏⢎⢎⢆⢄⠀⢑⣽⣿⢝⠲⠉⠀⠀⠀⠀
            ⠀⠀⠀⠀⠀⡿⠂⠠⠀⡇⢇⠕⢈⣀⠀⠁⠡⠣⡣⡫⣂⣿⠯⢪⠰⠂⠀⠀⠀⠀
            ⠀⠀⠀⠀⡦⡙⡂⢀⢤⢣⠣⡈⣾⡃⠠⠄⠀⡄⢱⣌⣶⢏⢊⠂⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⠀⢝⡲⣜⡮⡏⢎⢌⢂⠙⠢⠐⢀⢘⢵⣽⣿⡿⠁⠁⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⠀⠨⣺⡺⡕⡕⡱⡑⡆⡕⡅⡕⡜⡼⢽⡻⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⠀⣼⣳⣫⣾⣵⣗⡵⡱⡡⢣⢑⢕⢜⢕⡝⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⣴⣿⣾⣿⣿⣿⡿⡽⡑⢌⠪⡢⡣⣣⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⡟⡾⣿⢿⢿⢵⣽⣾⣼⣘⢸⢸⣞⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            ⠀⠀⠀⠀⠁⠇⠡⠩⡫⢿⣝⡻⡮⣒⢽⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
            —————————————————————————————
            """
            return

        try:
            async with self._redis.pipeline(transaction=False) as pipe:
                for quote in quotes:
                    key = self._make_key(quote)
                    payload = self._mapper.map_quote_to_ticker(quote).to_dict()

                    await pipe.setex(key, self._ttl, json.dumps(payload))

                await pipe.execute()

            logger.debug(
                "redis_batch_cached", quote_count=len(quotes), ttl_seconds=self._ttl
            )

            if settings.ENABLE_METRICS:
                metrics = get_metrics_registry()
                metrics.quotes_stored_total.labels(storage="redis").inc(len(quotes))

        except Exception as e:
            # Yep, we're silencing them.
            # It's just a cache layer anyway, it's fine if it fails.
            logger.error(
                "redis_batch_cache_failed",
                quote_count=len(quotes),
                error=str(e),
                exc_info=True,
            )

    @staticmethod
    def _make_key(quote: Quote) -> str:
        return f"quote:latest:{quote.pair}"
