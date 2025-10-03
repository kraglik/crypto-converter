from fastapi import HTTPException
from starlette import status

from converter.domain.exceptions.conversion import QuoteNotFoundError, QuoteTooOldError


def handle_domain_error(exc: Exception) -> HTTPException:
    if isinstance(exc, QuoteNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, QuoteTooOldError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    if isinstance(exc, ValueError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected internal error occurred.",
    )
