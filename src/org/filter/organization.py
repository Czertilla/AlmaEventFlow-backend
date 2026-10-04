from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from org.dto.organization import OrganizationFilterDTO
from org.enum.organization import OrganizationTypeEnum
from org.models.organization import OrganizationORM


class OrganizationFilter(
    OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1
):
    __dto_cls__ = OrganizationFilterDTO

    order_by: list[str] | None = ["name"]
    search: str | None = None
    type: OrganizationTypeEnum | None = None
    type__in: list[OrganizationTypeEnum] | None = None
    principal_id: UUID | None = None
    principal_id__isnull: bool | None = None
    address_id: UUID | None = None
    address_id__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = OrganizationORM
        search_model_fields = ["name", "acronym"]
        order_fields = ("name", "acronym", "type", "created_at", "edited_at")
