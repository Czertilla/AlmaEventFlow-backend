from uuid import UUID

from core.filter.identity import IdentityFilterMixin
from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from org.dto.collective import CollectiveFilterDTO
from org.models.collective import CollectiveORM


class CollectiveFilter(
    OrderedFilter,
    TimestampFilterMixin,
    IdentityFilterMixin,
    FromDTOMixinV1,
    ToDTOMixinV1,
):
    __dto_cls__ = CollectiveFilterDTO

    order_by: list[str] | None = ["name"]  # noqa: RUF012  # pydantic field default
    search: str | None = None
    principal_id: UUID | None = None
    principal_id__isnull: bool | None = None
    address_id: UUID | None = None
    address_id__isnull: bool | None = None
    university_id: UUID | None = None
    university_id__isnull: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = CollectiveORM
        search_model_fields = ["name", "acronym"]  # noqa: RUF012  # read-only constant of a plain class
        order_fields = ("name", "acronym", "created_at", "edited_at")
