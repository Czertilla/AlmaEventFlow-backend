from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import update

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin

from user.models.session import SessionORM as Model


class SessionRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_active_by_user(self, user_id: UUID) -> list[Model]:
        return await self.get_many(Model.user_id == user_id)

    async def update_last_used(self, session_id: UUID) -> None:
        stmt = (
            update(Model)
            .where(Model.id == session_id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await self.execute(stmt, flush=True)
