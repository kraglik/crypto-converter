import datetime
from decimal import Decimal

from converter.adapters.outbound.persistence.sqlalchemy.models import QuoteModel
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.values import Currency, Pair, TimestampUTC


class SQLAlchemyMapper:
    def __init__(self, rate_factory: RateFactory) -> None:
        self._rate_factory = rate_factory

    def db_model_to_quote(self, db_model: QuoteModel) -> Quote:
        # These fields are always present, but mypy things otherwise
        base_symbol = Currency(db_model.base_currency)  # type: ignore [arg-type]
        quote_symbol = Currency(db_model.quote_currency)  # type: ignore [arg-type]
        timestamp = TimestampUTC(db_model.quote_timestamp)  # type: ignore [arg-type]

        pair = Pair(base_symbol, quote_symbol)
        rate = self._rate_factory.from_string(str(db_model.rate))

        return Quote(
            pair=pair,
            timestamp=timestamp,
            rate=rate,
        )

    @staticmethod
    def quote_to_dict(quote: Quote) -> dict[str, str | Decimal | datetime.datetime]:
        symbol = quote.pair.code()

        return {
            "symbol": symbol,
            "quote_timestamp": quote.timestamp.value,
            "base_currency": quote.pair.base.code,
            "quote_currency": quote.pair.quote.code,
            "rate": quote.rate.value,
        }

    @staticmethod
    def quote_to_db_model(quote: Quote) -> QuoteModel:
        symbol = quote.pair.code()

        return QuoteModel(
            symbol=symbol,
            quote_timestamp=quote.timestamp.value,
            base_currency=quote.pair.base.code,
            quote_currency=quote.pair.quote.code,
            rate=quote.rate.value,  # type: ignore [arg-type]
        )
