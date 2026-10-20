from core.filter.ordered import OrderedFilter
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from geo.dto.city import CityFilterDTO
from geo.models.city import CityORM


class CityFilter(OrderedFilter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = CityFilterDTO

    order_by: list[str] | None = ["name"]  # noqa: RUF012  # pydantic field default
    search: str | None = None
    region_id: int | None = None
    region_id__in: list[int] | None = None

    class Constants(OrderedFilter.Constants):
        model = CityORM
        search_model_fields = ["name"]  # noqa: RUF012  # read-only constant of a plain class
        order_fields = ("name",)
