from profile.dto.diet import DietFilterDTO
from profile.models.diet import DietORM

from core.filter.ordered import OrderedFilter
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class DietFilter(OrderedFilter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = DietFilterDTO

    order_by: list[str] | None = ["name"]  # noqa: RUF012  # pydantic field default
    search: str | None = None

    class Constants(OrderedFilter.Constants):
        model = DietORM
        search_model_fields = ["name", "description"]  # noqa: RUF012  # read-only constant of a plain class
        order_fields = ("name",)
