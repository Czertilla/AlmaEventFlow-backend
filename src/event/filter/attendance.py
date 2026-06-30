from uuid import UUID

from fastapi_filter.contrib.sqlalchemy import Filter
from event.models.attendance import AttendanceORM


class AttendanceFilter(Filter):
    order_by: list[str] | None = ["created_at"]
    search: None | str = None
    participation_id: None | UUID = None
    participation_id__in: None | list[UUID] = None
    edited_at__isnull: bool | None = None
    member_id: None | UUID = None
    class Constants(Filter.Constants):
        model = AttendanceORM
        search_model_fields = ["comment"]