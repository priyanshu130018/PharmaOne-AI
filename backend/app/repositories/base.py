from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async data-access helper. Repositories own all DB queries so
    services never touch SQLAlchemy directly."""

    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: UUID) -> ModelType | None:
        return await self.session.get(self.model, entity_id)

    async def add(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelType) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return int(result.scalar_one())
