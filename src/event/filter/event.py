from datetime import date
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1
from event.models.event import (
    EventORM,
    EventLevelORM,
    EventStatusORM,
    EventTypeORM,
)
from event.models.participation import ParticipationORM


class EventFilter(Filter):
    order_by: list[str] | None = ["date"]
    search: None | str = None
    status: None | EventStatusEnumV1 = None
    level: None | EventLevelEnumV1 = None
    type: None | EventTypeEnumV1 = None
    format: None | EventFormatEnumV1 = None
    date__gte: None | date = None
    date__lte: None | date = None

    level__in: None | list[EventLevelEnumV1] = None
    type__in: None | list[EventTypeEnumV1] = None
    format__in: None | list[EventFormatEnumV1] = None

    participant_id: None | UUID = None
    participant_id__in: None | list[UUID] = None

    class Constants(Filter.Constants):
        model = EventORM
        search_model_fields = ["name", "description"]

    def filter(self, query):
        orig_status = self.status
        orig_level = self.level
        orig_type = self.type
        orig_format = self.format
        orig_participant = self.participant_id
        orig_participant_in = self.participant_id__in

        if orig_status is not None:
            query = query.join(EventORM.status_rel).filter(
                EventStatusORM.name == orig_status.value
            )

        if orig_level is not None:
            query = query.join(EventORM.level_rel).filter(
                EventLevelORM.name == orig_level.value
            )

        if orig_type is not None:
            query = query.join(EventORM.type_rel).filter(
                EventTypeORM.name == orig_type.value
            )

        if orig_participant is not None:
            query = query.where(
                EventORM.participations.any(
                    ParticipationORM.collective_id == orig_participant
                )
            )

        if orig_participant_in:
            query = query.where(
                EventORM.participations.any(
                    ParticipationORM.collective_id.in_(orig_participant_in)
                )
            )

        self.status = None
        self.level = None
        self.type = None
        self.format = None
        self.participant_id = None
        self.participant_id__in = None

        try:
            return super().filter(query)
        finally:
            self.status = orig_status
            self.level = orig_level
            self.type = orig_type
            self.format = orig_format
            self.participant_id = orig_participant
            self.participant_id__in = orig_participant_in
