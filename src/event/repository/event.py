from collections.abc import Sequence
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)
from core.dto.pagination import PageParams
from event.enum.status import EventStatusEnumV1
from event.models.event import EventLevelORM, EventStatusORM, EventTypeORM
from event.models.event import EventORM as Model
from event.models.participation import ParticipationORM


class EventRepo(
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
        _options = (
            selectinload(Model.status_rel),
            selectinload(Model.level_rel),
            selectinload(Model.type_rel),
        )
        if options:
            _options = (*_options, *options)
        return await super().search(
            filter, pagination, options=_options, scope=scope
        )

    async def status_id(self, name: str) -> int:
        stmt = select(EventStatusORM.id).where(EventStatusORM.name == name)
        return (await self.execute(stmt)).scalar_one()

    async def level_id(self, name: str) -> int:
        stmt = select(EventLevelORM.id).where(EventLevelORM.name == name)
        return (await self.execute(stmt)).scalar_one()

    async def type_id(self, name: str) -> int:
        stmt = select(EventTypeORM.id).where(EventTypeORM.name == name)
        return (await self.execute(stmt)).scalar_one()

    def _templates_of(self, collective_id: UUID):
        return (
            select(self.model)
            .join(ParticipationORM, ParticipationORM.event_id == self.model.id)
            .join(EventStatusORM, EventStatusORM.id == self.model.status_id)
            .where(
                ParticipationORM.collective_id == collective_id,
                EventStatusORM.name == EventStatusEnumV1.template.value,
            )
        )

    async def templates_of(self, collective_id: UUID) -> list[Model]:
        stmt = self._templates_of(collective_id)
        return list((await self.execute(stmt)).unique().scalars())

    async def get_template(
        self, template_id: UUID, collective_id: UUID
    ) -> Model | None:
        stmt = self._templates_of(collective_id).where(self.model.id == template_id)
        return (await self.execute(stmt)).unique().scalar_one_or_none()


class EventStatusRepo(
    SQLAlchemyRepository[EventStatusORM],
    IDRepositoryMixin[EventStatusORM, int],
    UpsertRepositoryMixin[EventStatusORM, int],
):
    model = EventStatusORM
