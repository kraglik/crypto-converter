from .base import DomainException


class QuoteError(DomainException):
    """Base exception for quote-related errors."""

    pass


class InvalidQuoteError(QuoteError):
    def __init__(self, reason: str):
        super().__init__(f"Invalid quote: {reason}")


class QuoteStorageError(QuoteError):
    """Raised when there's an error storing or retrieving quotes."""

    def __init__(self, operation: str, reason: str):
        self.operation = operation

        super().__init__(f"Quote storage error during {operation}: {reason}")
