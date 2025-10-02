from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field, field_validator

from converter.app.queries.get_conversion import ConversionResult, GetConversionQuery
from converter.domain.services.factory import AmountFactory
from converter.domain.values import Currency, Pair, TimestampUTC


class ConvertRequest(BaseModel):
    amount: Decimal = Field(
        gt=0, lt=Decimal("1e15"), description="The amount to convert.", examples=[1.5]
    )
    from_currency: str = Field(
        min_length=2,
        max_length=10,
        description="Source currency code.",
        examples=["BTC"],
    )
    to_currency: str = Field(
        min_length=2,
        max_length=10,
        description="Target currency code.",
        examples=["USDT"],
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Optional timestamp for historical conversion..",
        examples=["2025-10-02T10:00:00Z"],
    )

    @field_validator("from_currency", "to_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if not v.replace("_", "").isalnum():
            raise ValueError(
                f"Currency must only contain letters, numbers, and underscores: {v}"
            )
        return v.upper()

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            return v

        if v.tzinfo is None:
            raise ValueError("Timestamp must have a timezone")

        now = datetime.now(timezone.utc)

        if v > now:
            raise ValueError("Timestamp cannot be in the future")

        max_age = timedelta(days=7)
        if v < now - max_age:
            raise ValueError(f"Timestamp cannot be older than {max_age.days} days")

        return v

    @field_validator("to_currency")
    @classmethod
    def validate_different_currencies(cls, v: str, info) -> str:
        if "from_currency" in info.data and v == info.data["from_currency"]:
            raise ValueError("Source and target currencies must be different")
        return v


class ConversionResponse(BaseModel):
    amount: Decimal = Field(
        ...,
        description="The converted amount in the target currency.",
        examples=[12345.67],
    )
    rate: Decimal = Field(
        ..., description="The conversion rate used.", examples=[12345.67]
    )
    timestamp: datetime = Field(
        ...,
        description="The UTC timestamp of the quote used.",
        examples=["2025-10-02T10:00:00Z"],
    )

    class Config:
        json_encoders = {Decimal: str}


class ConversionQueryMapper:
    def __init__(
        self,
        amount_factory: AmountFactory,
    ) -> None:
        self._amount_factory = amount_factory

    def map_request_to_query(self, request: ConvertRequest) -> GetConversionQuery:
        base = Currency(request.from_currency)
        quote = Currency(request.to_currency)
        amount = self._amount_factory.create(request.amount)
        timestamp = TimestampUTC(request.timestamp) if request.timestamp else None

        pair = Pair(base, quote)

        return GetConversionQuery(
            pair=pair,
            amount=amount,
            at_timestamp=timestamp,
        )

    @staticmethod
    def map_conversion_result_to_response(
        result: ConversionResult,
    ) -> ConversionResponse:
        return ConversionResponse(
            amount=result.amount.value,
            timestamp=result.timestamp.value,
            rate=result.rate.value,
        )


async def parse_convert_request(
    amount: Decimal = Query(gt=0, examples=[1.5]),
    from_currency: str = Query(
        alias="from", min_length=2, max_length=10, examples=["BTC"]
    ),
    to_currency: str = Query(
        alias="to", min_length=2, max_length=10, examples=["USDT"]
    ),
    timestamp: Optional[datetime] = Query(
        default=None, examples=["2025-10-02T10:00:00Z"]
    ),
) -> ConvertRequest:
    return ConvertRequest(
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
        timestamp=timestamp,
    )
