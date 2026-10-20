from collections.abc import Sequence
from profile.models.passport import NameVariantORM
from profile.models.passport import PassportORM as Model
from typing import Any
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import ColumnElement, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import ExecutableOption

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.dto.pagination import PageParams


class PassportRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    with_name_variant = joinedload(Model.name_variant)

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
            options=options or (self.with_name_variant,),
            scope=scope,
        )

    async def add_n_return(
        self,
        data: dict[str, Any],
        options: tuple[Any, ...] = (with_name_variant,),
    ) -> Model:
        return await super().add_n_return(data, options)

    async def get_by_id(
        self, id: UUID, options: tuple[Any, ...] | None = (with_name_variant,)
    ) -> Model | None:
        return await super().get_by_id(id, options)

    async def clear_by_profile(self, profile_id: UUID):
        await self.execute(delete(Model).where(Model.profile_id == profile_id))


class NameVariantRepo(
    SQLAlchemyRepository[NameVariantORM],
    IDRepositoryMixin[NameVariantORM, UUID],
    UpsertRepositoryMixin[NameVariantORM, UUID],
):
    model = NameVariantORM
