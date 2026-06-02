from uuid import UUID
from fastapi_filter.contrib.sqlalchemy import Filter
from event.models.stage import EventStageORM


class StageFilter(Filter):
    order_by: list[str] | None = ["name"]
    search: None | str = None
    event_id: UUID | None = None

    class Constants(Filter.Constants):
        model = EventStageORM
        search_model_fields = ["name", "description"]
