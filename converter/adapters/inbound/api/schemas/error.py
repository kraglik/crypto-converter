from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(
        ...,
        description="A human-readable description of the error.",
        examples=["Quote not found for pair BTC/XYZ"],
    )
