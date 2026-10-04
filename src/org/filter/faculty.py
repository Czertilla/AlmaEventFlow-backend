from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from org.dto.faculty import FacultyFilterDTO
from org.models.faculty import FacultyORM


class FacultyFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = FacultyFilterDTO

    order_by: list[str] | None = ["name"]
    search: str | None = None
    principal_id: UUID | None = None
    principal_id__isnull: bool | None = None
    address_id: UUID | None = None
    address_id__isnull: bool | None = None
    university_id: UUID | None = None
    university_id__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = FacultyORM
        search_model_fields = ["name", "acronym"]
        order_fields = ("name", "acronym", "created_at", "edited_at")
