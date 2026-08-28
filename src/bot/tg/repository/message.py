from uuid import UUID

from sqlalchemy import select

from bot.tg.model.message import TelegramMessageORM as Model
from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin


class TelegramMessageRepo(
    SQLAlchemyRepository[Model], IDRepositoryMixin[Model, UUID]
):
    model = Model

    async def get(
        self, correlation_key: str, chat_id: int
    ) -> Model | None:
        stmt = select(Model).where(
            Model.correlation_key == correlation_key,
            Model.chat_id == chat_id,
        )
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def upsert(
        self, correlation_key: str, chat_id: int, message_id: int
    ) -> Model:
        existing = await self.get(correlation_key, chat_id)
        if existing is not None:
            return await self.update_one(
                existing.id, {"message_id": message_id}
            )
        return await self.add_n_return(
            {
                "correlation_key": correlation_key,
                "chat_id": chat_id,
                "message_id": message_id,
            }
        )
