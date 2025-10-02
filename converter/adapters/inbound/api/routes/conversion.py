import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from starlette import status

from converter.adapters.inbound.api.dependencies import (
    get_amount_factory,
    get_conversion_query_handler,
)
from converter.adapters.inbound.api.error_handler import handle_domain_error
from converter.adapters.inbound.api.schemas.conversion import (
    ConversionQueryMapper,
    ConversionResponse,
    ConvertRequest,
    parse_convert_request,
)
from converter.adapters.inbound.api.schemas.error import ErrorResponse
from converter.app.queries.get_conversion import GetConversionQueryHandler
from converter.domain.exceptions.conversion import QuoteNotFoundError, QuoteTooOldError
from converter.domain.services.factory import AmountFactory
from converter.shared.config import get_settings
from converter.shared.logging import get_logger
from converter.shared.observability import get_metrics_registry

logger = get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/convert", tags=["Conversion"])


@router.get(
    "",
    response_model=ConversionResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid input parameters",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "No quote found for this pair",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse,
            "description": "Quote is too old or validation error",
        },
    },
    summary="Convert Currency Amount",
    description="Provide crypto token conversion estimate based on latest binance rates",
)
async def convert_currency(
    request: ConvertRequest = Depends(parse_convert_request),
    handler: GetConversionQueryHandler = Depends(get_conversion_query_handler),
    amount_factory: AmountFactory = Depends(get_amount_factory),
) -> ConversionResponse:
    start_time = time.time()
    pair_str = f"{request.from_currency}{request.to_currency}"

    mapper = ConversionQueryMapper(amount_factory=amount_factory)

    try:
        query = mapper.map_request_to_query(request)

        logger.info(
            "conversion_requested",
            pair=pair_str,
            amount=str(request.amount),
            timestamp=request.timestamp.isoformat() if request.timestamp else None,
        )

        result = await handler.handle(query)

        duration = time.time() - start_time

        logger.info(
            "conversion_completed",
            pair=pair_str,
            rate=str(result.rate),
            converted_amount=str(result.amount),
            duration_ms=round(duration * 1000, 2),
        )

        if settings.ENABLE_METRICS:
            metrics = get_metrics_registry()
            metrics.conversions_total.labels(pair=pair_str, status="success").inc()
            metrics.conversion_duration_seconds.labels(pair=pair_str).observe(duration)

        return mapper.map_conversion_result_to_response(result)

    except ValidationError as e:
        duration = time.time() - start_time

        logger.warning(
            "conversion_validation_failed",
            pair=pair_str,
            errors=e.errors(),
            duration_ms=round(duration * 1000, 2),
        )

        error_messages = []

        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            error_messages.append(f"{field}: {msg}")

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="; ".join(error_messages),
        )

    except ValueError as e:
        duration = time.time() - start_time

        logger.warning(
            "conversion_domain_validation_failed",
            pair=pair_str,
            error=str(e),
            duration_ms=round(duration * 1000, 2),
        )

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except (QuoteNotFoundError, QuoteTooOldError) as e:
        duration = time.time() - start_time

        logger.warning(
            "conversion_failed",
            pair=pair_str,
            error_type=type(e).__name__,
            error=str(e),
            duration_ms=round(duration * 1000, 2),
        )

        if settings.ENABLE_METRICS:
            metrics = get_metrics_registry()
            metrics.conversions_total.labels(
                pair=pair_str, status=type(e).__name__
            ).inc()

        raise handle_domain_error(e)

    except Exception as e:
        duration = time.time() - start_time

        logger.error(
            "conversion_unexpected_error",
            pair=pair_str,
            error_type=type(e).__name__,
            error=str(e),
            duration_ms=round(duration * 1000, 2),
            exc_info=True,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during conversion",
        )
