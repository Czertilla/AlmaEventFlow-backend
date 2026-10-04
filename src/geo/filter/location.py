from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from geo.dto.location import LocationFilterDTO
from geo.models.location import LocationORM


class LocationFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = LocationFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    address_id: UUID | None = None
    address_id__in: list[UUID] | None = None
    name__isnull: bool | None = None
    spot__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = LocationORM
        search_model_fields = ["name"]
        order_fields = ("name", "created_at", "edited_at")
