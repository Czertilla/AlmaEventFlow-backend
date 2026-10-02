from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from geo.dto.location import LocationFilterDTO
from geo.models.location import LocationORM


class LocationFilter(Filter, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = LocationFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    address_id: UUID | None = None
    name__isnull: bool | None = None

    class Constants(Filter.Constants):
        model = LocationORM
        search_model_fields = ["name"]
