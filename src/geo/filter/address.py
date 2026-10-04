from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from geo.dto.address import AddressFilterDTO
from geo.models.address import AddressORM


class AddressFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = AddressFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    city_id: int | None = None
    city_id__in: list[int] | None = None
    source: str | None = None
    source__isnull: bool | None = None
    spot__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = AddressORM
        search_model_fields = ["name"]
        order_fields = ("name", "created_at", "edited_at")
