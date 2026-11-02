from datetime import datetime
from profile.enum.access import AccessAction
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1


class AccessFieldRead(BaseModel):
    key: str
    label: str

    model_config = ConfigDict(from_attributes=True)


class AccessLogEntryRead(FromDTOMixinV1, BaseModel):
    id: UUID
    created_at: datetime
    action: AccessAction
    outcome: str = Field(description="`ok`, or the code of the refusal.")
    fields: list[AccessFieldRead]
    by_self: bool
    by_administrator: bool
    actor_person_id: UUID | None
    actor_name: str | None
    request_id: UUID | None
    comment: str | None = Field(
        description="Why the data was asked for, as the requester wrote it."
    )

    model_config = ConfigDict(from_attributes=True)
