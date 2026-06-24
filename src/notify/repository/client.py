from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select, update

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin
from core.enum.notify import TransportTypeEnum

from notify.models.client import ClientORM as Model


class ClientRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_by_user(self, user_id: UUID) -> list[Model]:
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)
            .order_by(self.model.created_at.desc())
        )
        return (await self.execute(stmt)).scalars().all()

    async def get_active(
        self, user_id: UUID, transport: TransportTypeEnum
    ) -> list[Model]:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.transport == transport,
            self.model.is_active.is_(True),
        )
        return (await self.execute(stmt)).scalars().all()

    async def get_by_endpoint(
        self, user_id: UUID, transport: TransportTypeEnum, endpoint: str
    ) -> Model | None:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.transport == transport,
            self.model.endpoint == endpoint,
        )
        return (await self.execute(stmt)).scalar_one_or_none()

    async def deactivate(self, client_ids: Iterable[UUID]) -> None:
        ids = list(client_ids)
        if not ids:
            return
        await self.execute(
            update(self.model)
            .where(self.model.id.in_(ids))
            .values(is_active=False)
        )
