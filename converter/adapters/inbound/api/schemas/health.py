from typing import Optional

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    status: str = Field(
        ...,
        description="Status of the dependency (e.g., 'healthy').",
        examples=["healthy"],
    )
    error: Optional[str] = Field(
        None,
        description="Error message if unhealthy.",
        examples=["Connection timed out."],
    )


class ServiceHealthResponse(BaseModel):
    status: str = Field(
        ..., description="Overall service status.", examples=["healthy"]
    )
    checks: dict[str, HealthCheckResponse]
