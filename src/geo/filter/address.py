from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from geo.dto.address import AddressFilterDTO
from geo.models.address import AddressORM


class AddressFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = AddressFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    city_id: int | None = None
    class Constants(Filter.Constants):
        model = AddressORM
        search_model_fields = ["name"]
