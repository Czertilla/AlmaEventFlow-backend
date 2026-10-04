from uuid import UUID

from core.filter.ordered import OrderedFilter
from core.filter.timestamps import TimestampFilterMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.dto.attendance import AttendanceFilterDTO
from event.models.attendance import AttendanceORM


class AttendanceFilter(
    OrderedFilter, TimestampFilterMixin, FromDTOMixinV1, ToDTOMixinV1
):
    __dto_cls__ = AttendanceFilterDTO

    order_by: list[str] | None = ["created_at"]
    search: None | str = None
    participation_id: None | UUID = None
    participation_id__in: None | list[UUID] = None
    member_id: None | UUID = None
    member_id__in: None | list[UUID] = None
    is_attended: None | bool = None
    is_verified: None | bool = None

    class Constants(OrderedFilter.Constants):
        model = AttendanceORM
        search_model_fields = ["comment"]
        order_fields = ("is_attended", "is_verified", "created_at", "edited_at")
