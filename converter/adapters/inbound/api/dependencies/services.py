from typing import cast

import redis.asyncio as redis
from fastapi import Depends

from converter.app.queries.get_conversion import GetConversionQueryHandler
from converter.domain.services.factory import AmountFactory
from converter.shared.di import Container

from .container import get_container_dependency


def get_amount_factory(
    container: Container = Depends(get_container_dependency),
) -> AmountFactory:
    return container.amount_factory()


def get_conversion_query_handler(
    container: Container = Depends(get_container_dependency),
) -> GetConversionQueryHandler:
    return container.conversion_query_handler()


def get_redis_client(
    container: Container = Depends(get_container_dependency),
) -> redis.Redis:
    return cast(redis.Redis, container.redis_client())
