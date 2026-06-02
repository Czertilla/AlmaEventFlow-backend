from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from event.enum.priority import Priority
from event.schema.event import EventCreate
from event.schema.stage import StageCreateData


class MeParticipationCreate(BaseModel):
    event_id: UUID
    priority_degree: Priority | None = Field(alias="priority", default=None)
    member_ids: list[UUID] | None = None

    model_config = ConfigDict(from_attributes=True)


class MeEventCreate(EventCreate):
    collective_id: UUID
    member_ids: list[UUID] | None = None
    stages: list[StageCreateData] | None = None


class MeEventRead(EventCreate, BaseModel):
    id: UUID
    participation_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class MeAttendanceCreateData(BaseModel):
    member_id: UUID
    is_attended: bool | None = True
    is_verified: bool | None = True
    comment: str | None = Field(max_length=512, default=None)
