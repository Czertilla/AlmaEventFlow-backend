from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from org.dto.university import UniversityFilterDTO
from org.models.university import UniversityORM


class UniversityFilter(
    OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1
):
    __dto_cls__ = UniversityFilterDTO

    order_by: list[str] | None = ["name"]
    search: str | None = None
    principal_id: UUID | None = None
    principal_id__isnull: bool | None = None
    address_id: UUID | None = None
    address_id__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = UniversityORM
        search_model_fields = ["name", "acronym"]
        order_fields = ("name", "acronym", "created_at", "edited_at")
