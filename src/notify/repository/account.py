from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import update

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
