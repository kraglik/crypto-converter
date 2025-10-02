from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from converter.adapters.inbound.api.dependencies.container import (
    get_container_dependency,
)
from converter.shared.di import Container


async def get_db_session(
    container: Container = Depends(get_container_dependency),
) -> AsyncIterator[AsyncSession]:
    session_factory = container.db_session_factory()

    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
