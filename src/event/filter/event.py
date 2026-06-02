from datetime import date
from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from event.enum.status import EventStatus
from event.models.event import EventORM, EventStatusORM
from event.models.participation import ParticipationORM


class EventFilter(Filter):
    order_by: list[str] | None = ["date"]
    search: None | str = None
    status: None | EventStatus = None
    date__gte: None | date = None
    date__lte: None | date = None

    participant_id: None | UUID = None

    class Constants(Filter.Constants):
        model = EventORM
        search_model_fields = ["name", "description"]

    def filter(self, query):
        orig_status = self.status
        orig_participant = self.participant_id

        if orig_status is not None:
            query = (
                query.join(EventORM.status_rel)
                .filter(EventStatusORM.name == orig_status.value)
            )

        if orig_participant is not None:
            query = query.where(
                EventORM.participations.any(
                    ParticipationORM.collective_id == orig_participant
                )
            )

        self.status = None
        self.participant_id = None

        try:
            return super().filter(query)
        finally:
            self.status = orig_status
            self.participant_id = orig_participant