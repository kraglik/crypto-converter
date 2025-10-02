from datetime import datetime, timezone
from decimal import Decimal

from converter.adapters.outbound.persistence.sqlalchemy.mapper import SQLAlchemyMapper
from converter.adapters.outbound.persistence.sqlalchemy.models import QuoteModel
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.services.precision_service import PrecisionService
from converter.domain.values import Currency, Pair, Rate, TimestampUTC


def _quote():
    return Quote(
        pair=Pair(Currency("BTC"), Currency("USDT")),
        rate=Rate(Decimal("123.45678901")),
        timestamp=TimestampUTC(datetime(2025, 10, 2, 0, 0, 0, tzinfo=timezone.utc)),
    )


def test_quote_to_dict_and_model_roundtrip():
    # GIven
    mapper = SQLAlchemyMapper(rate_factory=RateFactory(PrecisionService()))
    q = _quote()

    # When
    d = mapper.quote_to_dict(q)
    model = mapper.quote_to_db_model(q)
    q2 = mapper.db_model_to_quote(model)

    # The
    assert d["symbol"] == "BTCUSDT"
    assert d["base_currency"] == "BTC"
    assert d["quote_currency"] == "USDT"
    assert d["rate"] == Decimal("123.45678901")

    assert isinstance(model, QuoteModel)
    assert model.symbol == "BTCUSDT"
    assert q2.pair == q.pair
    assert q2.rate.value == q.rate.value
    assert q2.timestamp.value == q.timestamp.value
