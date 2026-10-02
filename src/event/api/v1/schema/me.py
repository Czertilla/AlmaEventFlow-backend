from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.api.v1.schema.event import EventCreate
from event.api.v1.schema.stage import StageCreateData
from event.dto.me import (
    MeAttendanceCreateDataDTO,
    MeEventCreateDTO,
    MeParticipationCreateDTO,
)
from event.enum.priority import EventPriorityEnumV1


class MeParticipationCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = MeParticipationCreateDTO

    event_id: UUID
    priority_degree: EventPriorityEnumV1 | None = Field(
        default=None,
        validation_alias=AliasChoices("priority_degree", "EventPriorityEnumV1"),
    )
    member_ids: list[UUID] | None = None

    model_config = ConfigDict(from_attributes=True)


class MeEventCreate(EventCreate, ToDTOMixinV1):
    __dto_cls__ = MeEventCreateDTO

    collective_id: UUID
    member_ids: list[UUID] | None = None
    stages: list[StageCreateData] | None = None
    template_id: UUID | None = None
    """Start from one of the collective's ``status=template`` events --
    its fields (location included) become defaults for whichever fields
    this request didn't itself set explicitly."""


class MeEventRead(FromDTOMixinV1, EventCreate, BaseModel):
    id: UUID
    participation_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class MeAttendanceCreateData(BaseModel, ToDTOMixinV1):
    __dto_cls__ = MeAttendanceCreateDataDTO

    member_id: UUID
    is_attended: bool | None = True
    is_verified: bool | None = False
    comment: str | None = Field(max_length=512, default=None)
