from datetime import datetime
from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.stage import StageFilterDTO
from event.models.stage import EventStageORM


class StageFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = StageFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    event_id: UUID | None = None
    event_id__in: list[UUID] | None = None
    start_at__gte: datetime | None = None
    start_at__lte: datetime | None = None
    end_at__gte: datetime | None = None
    end_at__lte: datetime | None = None
    end_at__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = EventStageORM
        search_model_fields = ["name", "description"]
        order_fields = ("name", "start_at", "end_at", "created_at", "edited_at")
