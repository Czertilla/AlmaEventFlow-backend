from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.reward import RewardFilterDTO
from event.models.reward import RewardORM


class RewardFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = RewardFilterDTO

    order_by: list[str] | None = ["name"]  # noqa: RUF012  # pydantic field default
    search: str | None = None
    participation_id: UUID | None = None
    participation_id__in: list[UUID] | None = None
    degree: int | None = None
    degree__in: list[int] | None = None
    degree__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = RewardORM
        search_model_fields = ["name"]  # noqa: RUF012  # list[str] in fastapi-filter
        order_fields = ("name", "degree", "created_at", "edited_at")
