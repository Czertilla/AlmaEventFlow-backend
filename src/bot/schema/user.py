from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from core.schema.v1.mixin.model import FromAttributesV1


class User(BaseModel, FromAttributesV1):
    id: UUID
    created_at: datetime
    edited_at: datetime | None = None
