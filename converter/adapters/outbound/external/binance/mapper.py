from converter.adapters.outbound.external.binance.models import (
    BinanceServerTime,
    BinanceSymbolInfo,
    BinanceTicker,
)
from converter.domain.models import Quote
from converter.domain.services.factory import RateFactory
from converter.domain.values import Currency, Pair, TimestampUTC
from converter.shared.logging import get_logger

logger = get_logger(__name__)


class BinanceMapper:
    def __init__(self, rate_factory: RateFactory):
        self._rate_factory = rate_factory

    def ticker_to_quote(
        self, ticker: BinanceTicker, pair: Pair, timestamp: TimestampUTC
    ) -> Quote:
        rate = self._rate_factory.create(ticker.price)

        return Quote(pair=pair, rate=rate, timestamp=timestamp)

    def tickers_to_quotes(
        self, tickers: list[BinanceTicker], pairs: list[Pair], timestamp: TimestampUTC
    ) -> list[Quote]:
        ticker_map = {ticker.symbol: ticker for ticker in tickers}
        pair_map = {str(pair): pair for pair in pairs}

        quotes = []
        for symbol, pair in pair_map.items():
            ticker = ticker_map.get(symbol)
            if ticker is None:
                continue

            if ticker.price <= 0:
                logger.debug(
                    "skipping_zero_rate_ticker", symbol=symbol, price=str(ticker.price)
                )
                continue

            try:
                quote = self.ticker_to_quote(ticker, pair, timestamp)
                quotes.append(quote)
            except ValueError as e:
                logger.warning(
                    "invalid_ticker_skipped",
                    symbol=symbol,
                    price=str(ticker.price),
                    error=str(e),
                )
                continue

        return quotes

    @staticmethod
    def to_timestamp(server_time: BinanceServerTime) -> TimestampUTC:
        return TimestampUTC(server_time.as_datetime)

    @staticmethod
    def to_pair(symbol_info: BinanceSymbolInfo) -> Pair:
        base = Currency(symbol_info.base_asset)
        quote = Currency(symbol_info.quote_asset)
        return Pair(base=base, quote=quote)
