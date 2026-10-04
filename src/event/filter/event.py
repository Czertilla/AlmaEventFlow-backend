from datetime import date
from typing import Any
from uuid import UUID

from core.filter.ordered import OrderedFilter
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


class EventFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = EventFilterDTO

    order_by: list[str] | None = ["date"]
    search: None | str = None
    status: None | EventStatusEnumV1 = None
    status__in: None | list[EventStatusEnumV1] = None
    level: None | EventLevelEnumV1 = None
    type: None | EventTypeEnumV1 = None
    format: None | EventFormatEnumV1 = None
    date__gte: None | date = None
    date__lte: None | date = None
    date__isnull: None | bool = None
    level__in: None | list[EventLevelEnumV1] = None
    type__in: None | list[EventTypeEnumV1] = None
    format__in: None | list[EventFormatEnumV1] = None
    participant_id: None | UUID = None
    participant_id__in: None | list[UUID] = None
    organizer_id: None | UUID = None
    organizer_id__in: None | list[UUID] = None
    location_id: None | UUID = None
    location_id__in: None | list[UUID] = None
    location_id__isnull: None | bool = None

    class Constants(OrderedFilter.Constants):
        model = EventORM
        search_model_fields = ["name", "description"]
        order_fields = ("date", "name", "format", "created_at", "edited_at")

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
            return super().filter(query)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        finally:
            for name, value in given.items():
                setattr(self, name, value)
