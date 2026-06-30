from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from event.models.participation import ParticipationORM


class ParticipationFilter(Filter):
    order_by: list[str] | None = ["collective_id"]
    collective_id: None | UUID = None
    collective_id__in: None | list[UUID] = None
    event_id__in: None | list[UUID] = None

    class Constants(Filter.Constants):
        model = ParticipationORM
