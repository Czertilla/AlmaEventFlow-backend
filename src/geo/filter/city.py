from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from geo.dto.city import CityFilterDTO
from geo.models.city import CityORM


class CityFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = CityFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    region_id: int | None = None

    class Constants(Filter.Constants):
        model = CityORM
        search_model_fields = ["name"]
