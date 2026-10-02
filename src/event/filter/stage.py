from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.stage import StageFilterDTO
from event.models.stage import EventStageORM


class StageFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = StageFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    event_id: UUID | None = None
    event_id__in: None | list[UUID] = None

    class Constants(Filter.Constants):
        model = EventStageORM
        search_model_fields = ["name", "description"]
