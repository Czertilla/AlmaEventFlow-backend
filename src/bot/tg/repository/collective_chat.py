from uuid import UUID

from sqlalchemy import select, update

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

    async def get_by_collective_ids(
        self, collective_ids: list[UUID]
    ) -> list[Model]:
        if not collective_ids:
            return []
        stmt = select(Model).where(Model.collective_id.in_(collective_ids))
        return list((await self.execute(stmt)).unique().scalars().all())

    async def update_settings(
        self, collective_id: UUID, data: dict[str, bool | str | None]
    ) -> Model | None:
        existing = await self.get_by_collective_id(collective_id)
        if existing is None:
            return None
        return await self.update_one(existing.id, data, flush=True)

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
            updated = await self.update_one(existing.id, data, flush=True)
            if updated is None:
                raise LookupError(f"binding of {collective_id} disappeared")
            return updated
        return await self.add_n_return({"collective_id": collective_id, **data})

    async def move_chat(self, old_chat_id: int, new_chat_id: int) -> None:
        stmt = (
            update(Model)
            .where(Model.chat_id == old_chat_id)
            .values(chat_id=new_chat_id)
        )
        await self.execute(stmt, flush=True)
