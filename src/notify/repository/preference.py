from uuid import UUID

from sqlalchemy import delete, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin

from notify.models.preference import PreferenceORM as Model


class PreferenceRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_by_user(self, user_id: UUID) -> list[Model]:
        stmt = select(self.model).where(self.model.user_id == user_id)
        return (await self.execute(stmt)).scalars().all()

    async def delete_by_user(self, user_id: UUID) -> None:
        await self.execute(delete(self.model).where(self.model.user_id == user_id))
