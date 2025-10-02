from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from converter.shared.logging import get_logger

logger = get_logger(__name__)


def init_tracing(
    service_name: str = "crypto-converter",
    otlp_endpoint: Optional[str] = None,
    app: Optional[Any] = None,
    engine: Optional[Any] = None,
) -> None:
    if not otlp_endpoint:
        logger.info("tracing_disabled", reason="no_otlp_endpoint")
        return

    resource = Resource.create({"service.name": service_name})

    tracer_provider = TracerProvider(resource=resource)

    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)

    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

    trace.set_tracer_provider(tracer_provider)

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
        logger.debug("fastapi_instrumented")

    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.debug("sqlalchemy_instrumented")

    RedisInstrumentor().instrument()
    logger.debug("redis_instrumented")

    AioHttpClientInstrumentor().instrument()
    logger.debug("aiohttp_client_instrumented")

    logger.info(
        "tracing_initialized",
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        app_instrumented=app is not None,
        engine_instrumented=engine is not None,
    )


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
