from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin
from user.models.settings import UserSettingsORM as Model


class SettingsRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_for_user(self, user_id: UUID) -> Model | None:
        return await self.get_one(Model.user_id == user_id)

    async def lock_for_user(self, user_id: UUID) -> Model:
        """Row of ``user_id`` locked until the transaction ends, created empty
        when the user has none, so two first writes cannot both insert."""
        await self.execute(
            insert(Model)
            .values(user_id=user_id, data={}, revision=0)
            .on_conflict_do_nothing(index_elements=[Model.user_id])
        )
        stmt = select(Model).where(Model.user_id == user_id).with_for_update()
        return (await self.execute(stmt)).scalar_one()
