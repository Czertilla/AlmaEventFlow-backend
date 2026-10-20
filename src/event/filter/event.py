from datetime import date
from typing import Any
from uuid import UUID

from core.filter.identity import IdentityFilterMixin
from core.filter.ordered import OrderedFilter, ordered
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.event import EventFilterDTO
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1
from event.models.event import (
    EventLevelORM,
    EventORM,
    EventStatusORM,
    EventTypeORM,
)
from event.models.participation import ParticipationORM

RELATION_FILTERS = (
    "status",
    "status__in",
    "level",
    "level__in",
    "type",
    "type__in",
    "participant_id",
    "participant_id__in",
)


LOOKUP_ORDER = {
    "status": EventORM.status_id,
    "level": EventORM.level_id,
    "type": EventORM.type_id,
}


class EventFilter(
    OrderedFilter,
    TimestampFilterMixin,
    IdentityFilterMixin,
    FromDTOMixinV1,
    ToDTOMixinV1,
):
    __dto_cls__ = EventFilterDTO

    order_by: list[str] | None = ["date"]  # noqa: RUF012  # pydantic field default
    search: str | None = None
    status: EventStatusEnumV1 | None = None
    status__in: list[EventStatusEnumV1] | None = None
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 | None = None
    date__gte: date | None = None
    date__lte: date | None = None
    date__isnull: bool | None = None
    level__in: list[EventLevelEnumV1] | None = None
    type__in: list[EventTypeEnumV1] | None = None
    format__in: list[EventFormatEnumV1] | None = None
    participant_id: UUID | None = None
    participant_id__in: list[UUID] | None = None
    organizer_id: UUID | None = None
    organizer_id__in: list[UUID] | None = None
    location_id: UUID | None = None
    location_id__in: list[UUID] | None = None
    location_id__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = EventORM
        search_model_fields = ["name", "description"]  # noqa: RUF012  # list[str] in fastapi-filter
        order_fields = (
            "date",
            "name",
            "status",
            "level",
            "type",
            "format",
            "created_at",
            "edited_at",
        )

    def sort(self, query: Any) -> Any:
        entries: list[str] = self.ordering_values or []
        for entry in entries:
            name = entry.lstrip("+-")
            column = LOOKUP_ORDER.get(name)
            if column is None:
                column = getattr(EventORM, name)
            query = query.order_by(ordered(column, entry.startswith("-")))
        return query

    def filter(self, query: Any) -> Any:
        given = {name: getattr(self, name) for name in RELATION_FILTERS}
        if given["status"] is not None:
            query = query.join(EventORM.status_rel).filter(
                EventStatusORM.name == given["status"].value
            )
        if given["status__in"]:
            query = query.where(
                EventORM.status_rel.has(
                    EventStatusORM.name.in_([s.value for s in given["status__in"]])
                )
            )
        if given["level"] is not None:
            query = query.join(EventORM.level_rel).filter(
                EventLevelORM.name == given["level"].value
            )
        if given["level__in"]:
            query = query.where(
                EventORM.level_rel.has(
                    EventLevelORM.name.in_([v.value for v in given["level__in"]])
                )
            )
        if given["type"] is not None:
            query = query.join(EventORM.type_rel).filter(
                EventTypeORM.name == given["type"].value
            )
        if given["type__in"]:
            query = query.where(
                EventORM.type_rel.has(
                    EventTypeORM.name.in_([v.value for v in given["type__in"]])
                )
            )
        if given["participant_id"] is not None:
            query = query.where(
                EventORM.participations.any(
                    ParticipationORM.collective_id == given["participant_id"]
                )
            )
        if given["participant_id__in"]:
            query = query.where(
                EventORM.participations.any(
                    ParticipationORM.collective_id.in_(given["participant_id__in"])
                )
            )
        for name in RELATION_FILTERS:
            setattr(self, name, None)
        try:
            return super().filter(query)
        finally:
            for name, value in given.items():
                setattr(self, name, value)
