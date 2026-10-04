from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.role import RoleFilterDTO
from event.models.role import RoleORM


class RoleFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = RoleFilterDTO

    order_by: list[str] | None = ["name"]
    search: None | str = None
    collective_id: UUID | None = None
    collective_id__in: list[UUID] | None = None

    class Constants(OrderedFilter.Constants):
        model = RoleORM
        search_model_fields = ["name"]
        order_fields = ("name", "created_at", "edited_at")
