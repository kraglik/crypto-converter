from converter.domain.values import Pair

from .base import DomainException


class QuoteProviderError(DomainException):
    pass


class QuoteFetchError(QuoteProviderError):
    def __init__(self, pair: Pair, reason: str):
        self.pair = pair

        super().__init__(f"Failed to fetch quote for {pair}: {reason}")


class QuoteProviderUnavailableError(QuoteProviderError):
    def __init__(self, provider_name: str, reason: str):
        self.provider_name = provider_name

        super().__init__(f"Quote provider '{provider_name}' is unavailable: {reason}")
