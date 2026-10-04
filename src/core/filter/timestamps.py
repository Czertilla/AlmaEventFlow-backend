from datetime import datetime

from pydantic import BaseModel


class TimestampFilterMixin(BaseModel):
    created_at__gte: datetime | None = None
    created_at__lte: datetime | None = None
    edited_at__gte: datetime | None = None
    edited_at__lte: datetime | None = None
    edited_at__isnull: bool | None = None
