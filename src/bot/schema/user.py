from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from core.utils.mixin.pydantic import FromAttributes


class User(BaseModel, FromAttributes):
    id: UUID
    created_at: datetime
    edited_at: datetime | None = None
