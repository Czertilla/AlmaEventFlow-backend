from uuid import UUID

from sqlalchemy import select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)
from event.models.collective import CollectiveORM as Model
from event.models.member import MemberORM


class CollectiveRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID]
):
    model = Model

    async def get_by_principal_id(self, principal_id: UUID) -> list[Model]:
        stmt = select(self.model).where(self.model.principal_id == principal_id)
        return (await self.execute(stmt)).unique().scalars().all()

    async def get_by_member_person_id(self, person_id: UUID) -> list[Model]:
        stmt = (
            select(self.model)
            .join(MemberORM, MemberORM.collective_id == self.model.id)
            .where(MemberORM.person_id == person_id, MemberORM.is_active)
        )
        return list((await self.execute(stmt)).unique().scalars().all())
