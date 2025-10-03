import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from converter.adapters.inbound.api.dependencies import (
    get_db_session,
    get_redis_client,
)
from converter.adapters.inbound.api.schemas.health import (
    HealthCheckResponse,
    ServiceHealthResponse,
)
from converter.shared.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=ServiceHealthResponse,
    summary="Health Check",
    description="Check health status of all service dependencies",
)
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> ServiceHealthResponse:
    checks: dict[str, HealthCheckResponse] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["postgres"] = HealthCheckResponse(status="healthy", error=None)
        logger.debug("health_check_postgres", status="healthy")
    except Exception as e:
        checks["postgres"] = HealthCheckResponse(status="unhealthy", error=str(e))
        logger.warning("health_check_postgres", status="unhealthy", error=str(e))

    try:
        await redis_client.ping()
        checks["redis"] = HealthCheckResponse(status="healthy", error=None)
        logger.debug("health_check_redis", status="healthy")
    except Exception as e:
        checks["redis"] = HealthCheckResponse(status="unhealthy", error=str(e))
        logger.warning("health_check_redis", status="unhealthy", error=str(e))

    overall = (
        "healthy"
        if all(c.status == "healthy" for c in checks.values())
        else "unhealthy"
    )

    logger.info("health_check_complete", overall_status=overall)

    return ServiceHealthResponse(status=overall, checks=checks)
