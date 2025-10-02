from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import ValidationError
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from converter.adapters.inbound.api.routes import conversion, health
from converter.shared.config import get_settings
from converter.shared.di import cleanup_resources, get_container
from converter.shared.logging import configure_logging, get_logger
from converter.shared.observability import generate_metrics, init_metrics, init_tracing

settings = get_settings()

configure_logging(log_level=settings.LOG_LEVEL, json_logs=settings.JSON_LOGS)

logger = get_logger(__name__)

if settings.ENABLE_METRICS:
    init_metrics()
    logger.info("metrics_enabled")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("api_starting_up")

    container = get_container(app_type="api")
    setattr(app, "state", type("State", (), {"container": container})())

    try:
        redis_client = container.redis_client()
        await redis_client.ping()
        logger.info("redis_connection_verified")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e), exc_info=True)
        raise

    yield

    logger.info("api_shutting_down")

    await cleanup_resources(container)

    logger.info("api_shutdown_complete")


app = FastAPI(
    title="Crypto Converter API",
    description="API for estimating the resulting amount for crypto coins conversion",
    version="0.1.0",
    lifespan=lifespan,
)

if settings.ENABLE_TRACING and settings.OPEN_TELEMETRY_COLLECTOR_ENDPOINT:
    init_tracing(
        service_name="crypto-converter-api",
        otlp_endpoint=settings.OPEN_TELEMETRY_COLLECTOR_ENDPOINT,
        app=app,
    )
    logger.info("tracing_enabled")

app.include_router(conversion.router)
app.include_router(health.router)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    if not settings.ENABLE_METRICS:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Metrics are disabled"},
        )

    content, content_type = generate_metrics()
    return Response(content=content, media_type=content_type)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning(
        "request_validation_error",
        path=request.url.path,
        method=request.method,
        errors=exc.errors(),
    )

    error_messages = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        msg = error["msg"]
        error_messages.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(error_messages)},
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    logger.warning(
        "pydantic_validation_error",
        path=request.url.path,
        method=request.method,
        errors=exc.errors(),
    )

    error_messages = []

    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        msg = error["msg"]
        error_messages.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "; ".join(error_messages)},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger.warning(
        "domain_validation_error",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    logger.warning(
        "http_exception",
        path=request.url.path,
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred"},
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time

    from converter.shared.observability import get_metrics_registry

    start_time = time.time()

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )

        if settings.ENABLE_METRICS:
            mtr = get_metrics_registry()
            mtr.http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
            ).inc()
            mtr.http_request_duration_seconds.labels(
                method=request.method, endpoint=request.url.path
            ).observe(duration)

        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration_ms=round(duration * 1000, 2),
            exc_info=True,
        )
        raise
