import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1


class RecentLocationRead(FromDTOMixinV1, BaseModel):
    location_id: UUID
    used_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
