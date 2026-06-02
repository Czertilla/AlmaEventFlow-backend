from typing import Any, Generic
from sqlalchemy import Select, delete, exists, func, select, update
from sqlalchemy.sql.base import ExecutableOption
from fastapi_filter.contrib.sqlalchemy import Filter
from core.config.settings import settings
from core.schema.pagination import SPageParam

if settings.DB_DBMS == "postgres":
    from sqlalchemy.dialects.postgresql import insert
elif settings.DB_DBMS == "sqlite":
    from sqlalchemy.dialects.sqlite import insert

from ....utils.abstract.repository import (
    AbstractIdRepository,
    AbstractRepository,
)
from ..mixins.models import IDMixin as Model, ID


class IDRepositoryMixin(
    Generic[Model, ID], AbstractIdRepository, AbstractRepository
):
    model: type[Model]

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


class UpsertRepositoryMixin(
    Generic[Model, ID], AbstractIdRepository, AbstractRepository
):
    conflict_index_elements = ["id"]
    model: type[Model]

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


class SearchRepositoryMixin(Generic[Model], AbstractRepository):
    model: type[Model]

    @staticmethod
    def _apply_filter(filter: Filter, statement: Select):
        return filter.filter(filter.sort(statement))

    async def search(
        self,
        filter: Filter,
        pagination: SPageParam,
        *,
        options=None,
        scope: list | None = None,
    ) -> tuple[list[Model], int]:
        total_stmt = select(func.count()).select_from(self.model)
        if scope:
            total_stmt = total_stmt.where(*scope)
        total_stmt = filter.filter(total_stmt)
        total = (await self.execute(total_stmt)).scalar_one()
        if not total:
            return [], 0
        stmt = (
            select(self.model).limit(pagination.limit).offset(pagination.offset)
        )
        if options:
            stmt = stmt.options(*options)
        if scope:
            stmt = stmt.where(*scope)
        stmt = self._apply_filter(filter, stmt)
        return (await self.execute(stmt)).unique().scalars(), total
