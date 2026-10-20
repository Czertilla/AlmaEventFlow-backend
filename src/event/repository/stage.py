from collections.abc import Sequence
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import ColumnElement
from sqlalchemy.sql.base import ExecutableOption

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.dto.pagination import PageParams
from event.models.stage import EventStageORM as Model


class EventStageRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    async def search(
        self,
        filter: Filter,
        pagination: PageParams,
        *,
        options: Sequence[ExecutableOption] | None = None,
        scope: list[ColumnElement[bool]] | None = None,
    ):
        return await super().search(
            filter, pagination, options=options, scope=scope
        )
