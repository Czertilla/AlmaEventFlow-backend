from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.reward import RewardFilterDTO
from event.models.reward import RewardORM


class RewardFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = RewardFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None

    class Constants(Filter.Constants):
        model = RewardORM
        search_model_fields = ["name"]
