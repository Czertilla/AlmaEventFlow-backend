from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select, update

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)

from notify.models.account import AccountORM as Model


class AccountRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
):
    model = Model

    async def set_verified(self, ids: Iterable[UUID]) -> None:
        ids = list(ids)
        if not ids:
            return
        await self.execute(
            update(self.model)
            .where(self.model.id.in_(ids))
            .values(is_verified=True)
        )

    async def user_ids_by_persons(
        self, person_ids: Iterable[UUID]
    ) -> list[UUID]:
        person_ids = list(person_ids)
        if not person_ids:
            return []
        stmt = select(self.model.id).where(
            self.model.person_id.in_(person_ids)
        )
        return (await self.execute(stmt)).scalars().all()
