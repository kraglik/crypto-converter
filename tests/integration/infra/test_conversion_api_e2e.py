import importlib
from datetime import datetime, timezone
from decimal import Decimal

import converter.adapters.inbound.api.app as app_module
import pytest
from converter.adapters.outbound.persistence.redis.quote_writer import RedisQuoteWriter
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, Rate, TimestampUTC
from converter.shared.config import get_settings
from fastapi.testclient import TestClient


def _quote(ts: datetime) -> Quote:
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("25000")),
        timestamp=TimestampUTC(ts),
    )


@pytest.mark.asyncio
async def test_api_convert_with_real_infra(env_infra, redis_client):
    writer = RedisQuoteWriter(
        redis_client=redis_client,
        rate_factory=RateFactory(PrecisionService()),
        ttl_seconds=120,
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    q = _quote(now)
    await writer.save_batch([q])

    get_settings.cache_clear()
    app = importlib.reload(app_module).app

    with TestClient(app) as client:
        resp = client.get(
            "/convert", params={"amount": "2", "from": "BTC", "to": "USDT"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["amount"] == "50000.0000000000000000"
        assert data["rate"] == "25000.00000000"
        assert data["timestamp"].replace("Z", "+00:00") == now.isoformat()
