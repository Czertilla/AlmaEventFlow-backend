from collections.abc import Sequence
from profile.models.contact import ContactORM
from profile.models.passport import PassportORM
from profile.models.person import PersonORM
from profile.models.profile import ProfileORM as Model
from typing import Any
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import ColumnElement, update
from sqlalchemy.orm import joinedload, selectinload, with_loader_criteria
from sqlalchemy.sql.base import ExecutableOption

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.dto.pagination import PageParams


class ProfileRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    with_passports = selectinload(Model.passports).load_only(PassportORM.id)
    with_diet = joinedload(Model.diet)
    with_person = selectinload(Model.person).selectinload(PersonORM.contacts)
    with_workplace = selectinload(Model.workplace)
    with_main_contacts = with_loader_criteria(ContactORM, ContactORM.is_main)

    all_options = (
        with_passports,
        with_diet,
        with_person,
        with_workplace,
        with_main_contacts,
    )

    async def update_one(
        self,
        id: UUID,
        data: dict[str, Any],
        flush: bool = False,
        options: tuple[ExecutableOption, ...] = all_options,
    ) -> Model | None:
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**data)
            .returning(self.model)
            .options(*options)
        )
        return (await self.execute(stmt, flush)).unique().scalar_one_or_none()

    async def get_by_id(
        self, id: UUID, options: tuple[Any, ...] | None = all_options
    ) -> Model | None:
        return await super().get_by_id(id, options)

    async def add_n_return(
        self, data: dict[str, Any], options: tuple[Any, ...] = all_options
    ) -> Model:
        return await super().add_n_return(data, options)

    async def upsert(
        self,
        data: dict[str, Any],
        options: tuple[ExecutableOption, ...] = all_options,
    ) -> Model | None:
        return await super().upsert(data, options)

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
