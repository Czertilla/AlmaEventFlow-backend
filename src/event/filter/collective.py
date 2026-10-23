from uuid import UUID

from core.filter.identity import IdentityFilterMixin
from core.filter.ordered import OrderedFilter
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.collective import CollectiveFilterDTO
from event.models.collective import CollectiveORM


class CollectiveFilter(
    OrderedFilter,
    IdentityFilterMixin,
    FromDTOMixinV1,
    ToDTOMixinV1,
):
    __dto_cls__ = CollectiveFilterDTO

    order_by: list[str] | None = ["name"]  # noqa: RUF012  # pydantic field default
    search: str | None = None
    principal_id: UUID | None = None
    principal_id__in: list[UUID] | None = None
    is_verified: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = CollectiveORM
        search_model_fields = ["name"]  # noqa: RUF012  # list[str] in fastapi-filter
        order_fields = ("name", "is_verified")
