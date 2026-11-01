from profile.dto.passport import PassportFilterDTO
from profile.models.passport import PassportORM
from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class PassportFilter(OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = PassportFilterDTO

    order_by: list[str] | None = ["created_at"]  # noqa: RUF012  # pydantic field default
    search: str | None = None
    profile_id: UUID | None = None
    is_foreign: bool | None = None

    class Constants(OrderedFilter.Constants):
        model = PassportORM
        order_fields = ("is_foreign", "created_at", "edited_at")
