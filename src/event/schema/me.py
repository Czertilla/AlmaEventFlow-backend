from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from event.enum.priority import EventPriorityEnumV1
from event.schema.event import EventCreate
from event.schema.stage import StageCreateData


class MeParticipationCreate(BaseModel):
    event_id: UUID
    priority_degree: EventPriorityEnumV1 | None = Field(
        alias="EventPriorityEnumV1", default=None
    )
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
    # Новая отметка не заверена: руководитель заверяет осознанно отдельным действием
    is_verified: bool | None = False
    comment: str | None = Field(max_length=512, default=None)
