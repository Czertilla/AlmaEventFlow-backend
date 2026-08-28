from uuid import UUID

from sqlalchemy import select

from bot.tg.model.collective_chat import CollectiveChatORM as Model
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin


class CollectiveChatRepo(
    SQLAlchemyRepository[Model], IDRepositoryMixin[Model, UUID]
):
    model = Model

    async def get_by_collective_id(
        self, collective_id: UUID
    ) -> Model | None:
        stmt = select(Model).where(Model.collective_id == collective_id)
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def get_by_chat_id(self, chat_id: int) -> Model | None:
        stmt = select(Model).where(Model.chat_id == chat_id)
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def upsert(
        self,
        collective_id: UUID,
        chat_id: int,
        set_by_id: int,
        thread_id: int | None = None,
    ) -> Model:
        existing = await self.get_by_collective_id(collective_id)
        data = {
            "chat_id": chat_id,
            "thread_id": thread_id,
            "set_by_id": set_by_id,
        }
        if existing is not None:
            return await self.update_one(existing.id, data)
        return await self.add_n_return({"collective_id": collective_id, **data})
