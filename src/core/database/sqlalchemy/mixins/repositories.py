from abc import abstractmethod
from typing import Any, Generic
from sqlalchemy import Result, delete, exists, select, update
from sqlalchemy.sql.base import ExecutableOption
from core.config.settings import settings

if settings.DB_DBMS == "postgres":
    from sqlalchemy.dialects.postgresql import insert
elif settings.DB_DBMS == "sqlite":
    from sqlalchemy.dialects.sqlite import insert

from ....utils.abstract.repository import AbstractIdRepository
from ..mixins.models import IDMixin as Model, ID


class IDRepositoryMixin(Generic[Model, ID], AbstractIdRepository):
    model: type[Model]

    @abstractmethod
    async def execute(self, stmt, flush: bool = False) -> Result:
        raise NotImplementedError

    async def _get_with_options(self, id: ID, options: tuple) -> Model | None:
        stmt = select(self.model).where(self.model.id == id).options(*options)
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def get_by_id(self, id: ID, options: tuple = None) -> Model | None:
        if options:
            return await self._get_with_options(id, options)
        stmt = select(self.model).where(self.model.id == id)
        return (await self.execute(stmt)).unique().scalar_one_or_none()

    async def update_one(
        self, id: ID, data: dict[str, Any], flush: bool = False
    ) -> Model | None:
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
        )
        return (await self.execute(stmt, flush)).unique().scalar_one_or_none()

    async def update_many(
        self, data: dict[str, dict[str, Any]], options: tuple = ()
    ) -> None:
        stmt = (
            update(self.model)
            .where(self.model.id.in_(data.keys()))
            .values(**data)
            .options(*options)
        )
        return await self.execute(stmt, flush=True)

    async def exists_id(self, id: ID) -> bool:
        return (
            await self.execute(select(exists().where(self.model.id == id)))
        ).scalar()

    async def delete_one(self, id: ID) -> None:
        await self.execute(delete(self.model).where(self.model.id == id))


class UpsertRepositoryMixin(Generic[Model, ID], AbstractIdRepository):
    conflict_index_elements = ["id"]
    model: type[Model]

    @abstractmethod
    async def execute(self, stmt, flush: bool = False) -> Result:
        raise NotImplementedError

    def _get_set_data(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in data.items()
            if key not in self.conflict_index_elements
        }

    async def upsert(
        self, data: dict[str, Any], options: tuple[ExecutableOption] = ()
    ) -> Model | None:
        stmt = (
            insert(self.model)
            .values(**data)
            .on_conflict_do_update(
                index_elements=self.conflict_index_elements,
                set_=self._get_set_data(data),
            )
            .options(*options)
            .returning(self.model)
        )
        return (await self.execute(stmt)).scalar_one_or_none()
