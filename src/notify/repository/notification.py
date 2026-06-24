from uuid import UUID

from sqlalchemy import select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin

from notify.models.notification import NotificationORM as Model


class NotificationRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_by_event_id(self, event_id: UUID) -> Model | None:
        stmt = select(self.model).where(self.model.event_id == event_id)
        return (await self.execute(stmt)).scalar_one_or_none()
