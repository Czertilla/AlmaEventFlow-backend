from logging import getLogger
from typing import AsyncGenerator
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy import update as sa_update

from bot.tg.model.user import TGUserORM as Model
from core.config.settings import settings
from core.database.sqlalchemy.core import SQLAlchemyRepository

logger = getLogger(__name__)


class UserRepo(SQLAlchemyRepository[Model]):
    model = Model

    async def get_by_id(self, id: int) -> Model | None:
        return (
            await self.execute(select(Model).where(Model.id == id))
        ).scalar_one_or_none()

    async def get_by_user_id(self, user_id: UUID) -> Model | None:
        return (
            await self.execute(select(Model).where(Model.user_id == user_id))
        ).scalar_one_or_none()

    async def clear_link(self, user_id: UUID) -> None:
        stmt = (
            sa_update(Model)
            .where(Model.user_id == user_id)
            .values(user_id=None)
        )
        await self.execute(stmt, flush=True)

    async def update_one(self, id: int, data: dict) -> Model | None:
        stmt = (
            sa_update(Model)
            .where(Model.id == id)
            .values(**data)
            .returning(Model)
        )
        result = await self.execute(stmt)
        await self.flush()
        return result.scalar_one_or_none()

    async def delete_one(self, id: int) -> None:
        model = await self.get_by_id(id)
        if model:
            await self.session.delete(model)

    async def check_username(self, value: str) -> bool:
        return await self.count(self.model.username == value) > 0

    async def get_by_username(self, username: str) -> Model | None:
        logger.debug(f"getting user by {username=}")
        if not username:
            return None
        return (
            await self.execute(select(Model).where(Model.username == username))
        ).scalar_one_or_none()

    async def get_all_superusers_tg_id(self) -> list[int]:
        stmt = select(Model.id).where(Model.is_superuser)
        return (await self.execute(stmt)).unique().scalars().all()

    @staticmethod
    def _search_stmt(
        search_column: ColumnElement,
        query: str,
        limit: int = None,
        offset: int = 0,
    ):
        rank = func.similarity(search_column, query).label("rank")
        return (
            select(Model)
            .where(
                search_column.op("%")(query)
                if len(query) >= 4
                else search_column.ilike(f"%{query}%")
            )
            .order_by(rank.desc())
            .limit(limit or settings.MAX_PAGE_SIZE)
            .offset(offset)
        )

    async def search_by_username(
        self,
        query: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Model]:
        return (
            (
                await self.execute(
                    self._search_stmt(Model.username, query, limit, offset)
                )
            )
            .scalars()
            .all()
        )

    async def search_by_name(
        self,
        query: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Model]:
        full_name = func.concat(
            Model.first_name, " ", func.coalesce(Model.last_name, "")
        )
        return (
            (
                await self.execute(
                    self._search_stmt(full_name, query, limit, offset)
                )
            )
            .scalars()
            .all()
        )

    async def user_stream(self) -> AsyncGenerator[Model]:
        stmt = select(Model).where(Model.is_active)
        async for scalar in self.stream_scalars_generator(stmt):
            yield scalar
