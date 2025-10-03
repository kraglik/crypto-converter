from converter.adapters.inbound.api.error_handler import handle_domain_error
from converter.domain.exceptions.conversion import QuoteNotFoundError, QuoteTooOldError
from converter.domain.values import Currency, Pair
from converter.domain.values.quote_age import QuoteAge
from fastapi import HTTPException
from starlette import status


def test_error_handler_mappings():
    # Given
    pair = Pair(Currency("BTC"), Currency("USDT"))

    # When
    not_found = handle_domain_error(QuoteNotFoundError(pair))
    too_old = handle_domain_error(QuoteTooOldError(pair, QuoteAge(61), 60))
    bad = handle_domain_error(ValueError("oops"))
    unexpected = handle_domain_error(RuntimeError("boom"))

    # Then
    assert isinstance(not_found, HTTPException)
    assert not_found.status_code == status.HTTP_404_NOT_FOUND
    assert unexpected.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert too_old.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert bad.status_code == status.HTTP_400_BAD_REQUEST
