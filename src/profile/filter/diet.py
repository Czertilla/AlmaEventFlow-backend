from profile.dto.diet import DietFilterDTO
from profile.models.diet import DietORM

from core.filter.ordered import OrderedFilter
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class DietFilter(OrderedFilter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = DietFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None

    class Constants(OrderedFilter.Constants):
        model = DietORM
        search_model_fields = ["name", "description"]
        order_fields = ("name",)
