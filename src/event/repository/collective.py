from uuid import UUID
from sqlalchemy import select
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin, UpsertRepositoryMixin

from event.models.collective import CollectiveORM as Model


class CollectiveRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID]
):
    model = Model

    async def get_by_principal_id(self, principal_id: UUID) -> list[Model]:
        stmt = select(self.model).where(self.model.principal_id == principal_id)
        return (await self.execute(stmt)).unique().scalars().all()