from collections.abc import Sequence
from profile.models.contact import ContactORM
from profile.models.person import PersonORM as Model
from typing import Any
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import ColumnElement, select, update
from sqlalchemy.orm import selectinload, with_loader_criteria
from sqlalchemy.sql.base import ExecutableOption

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.dto.pagination import PageParams


class PersonRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    with_contacts = selectinload(Model.contacts)
    with_main_contacts = with_loader_criteria(ContactORM, ContactORM.is_main)
    all_options = (with_contacts, with_main_contacts)

    async def get_with_contacts(self, id: UUID) -> Model | None:
        return await self.get_by_id(
            id, (self.with_contacts, self.with_main_contacts)
        )

    async def add_n_return(
        self,
        data: dict[str, Any],
        options: tuple[Any, ...] = (with_contacts, with_main_contacts),
    ) -> Model:
        return await super().add_n_return(data, options)

    async def update_one(
        self, id: UUID, data: dict[str, Any], flush: bool = False
    ) -> Model | None:
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
            .options(*self.all_options)
        )
        return (await self.execute(stmt, flush)).unique().scalar_one_or_none()

    async def get_many_cron(
        self,
        offset: int,
        limit: int,
    ):
        stmt = (
            select(Model)
            .order_by(Model.edited_at)
            .order_by(Model.created_at)
            .limit(limit)
            .offset(offset)
            .options(*self.all_options)
        )
        return (
            (await self.execute(stmt)).unique().scalars().all(),
            await self.count(),
        )

    async def search(
        self,
        filter: Filter,
        pagination: PageParams,
        *,
        options: Sequence[ExecutableOption] | None = None,
        scope: list[ColumnElement[bool]] | None = None,
    ):
        return await super().search(
            filter,
            pagination,
            options=options or self.all_options,
            scope=scope,
        )

    async def upsert(
        self,
        data: dict[str, Any],
        options: tuple[ExecutableOption, ...] = all_options,
    ) -> Model | None:
        return await super().upsert(data, options)
