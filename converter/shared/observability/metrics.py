from functools import lru_cache
from typing import Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from converter.shared.logging import get_logger

logger = get_logger(__name__)


class Metrics:
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()

        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )
        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "endpoint"],
            registry=self.registry,
        )

        self.conversions_total = Counter(
            "conversions_total",
            "Total currency conversions",
            ["pair", "status"],
            registry=self.registry,
        )
        self.conversion_duration_seconds = Histogram(
            "conversion_duration_seconds",
            "Conversion processing time",
            ["pair"],
            registry=self.registry,
        )

        self.quotes_fetched_total = Counter(
            "quotes_fetched_total",
            "Total quotes fetched from external source",
            ["source"],
            registry=self.registry,
        )
        self.quotes_stored_total = Counter(
            "quotes_stored_total",
            "Total quotes stored",
            ["storage"],
            registry=self.registry,
        )
        self.quote_age_seconds = Gauge(
            "quote_age_seconds",
            "Age of the most recent quote",
            ["pair"],
            registry=self.registry,
        )

        self.cache_hits_total = Counter(
            "cache_hits_total",
            "Cache hit count",
            ["cache_type"],
            registry=self.registry,
        )
        self.cache_misses_total = Counter(
            "cache_misses_total",
            "Cache miss count",
            ["cache_type"],
            registry=self.registry,
        )

        self.db_queries_total = Counter(
            "db_queries_total",
            "Total database queries",
            ["operation", "table"],
            registry=self.registry,
        )
        self.db_query_duration_seconds = Histogram(
            "db_query_duration_seconds",
            "Database query duration",
            ["operation", "table"],
            registry=self.registry,
        )

        self.external_api_requests_total = Counter(
            "external_api_requests_total",
            "External API requests",
            ["provider", "endpoint", "status"],
            registry=self.registry,
        )
        self.external_api_duration_seconds = Histogram(
            "external_api_duration_seconds",
            "External API request duration",
            ["provider", "endpoint"],
            registry=self.registry,
        )

        logger.info("metrics_initialized")


@lru_cache()
def get_metrics_registry() -> Metrics:
    return Metrics()


def init_metrics() -> Metrics:
    get_metrics_registry.cache_clear()
    return get_metrics_registry()


def generate_metrics() -> tuple[str, str]:
    metrics = get_metrics_registry()
    content = generate_latest(metrics.registry)
    return content.decode("utf-8"), CONTENT_TYPE_LATEST
