from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.reward import RewardFilterDTO
from event.models.reward import RewardORM


class RewardFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = RewardFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    participation_id: UUID | None = None
    participation_id__in: list[UUID] | None = None
    degree: int | None = None
    degree__in: list[int] | None = None
    degree__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = RewardORM
        search_model_fields = ["name"]
        order_fields = ("name", "degree", "created_at", "edited_at")
