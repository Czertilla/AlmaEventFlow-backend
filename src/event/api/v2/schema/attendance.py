from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import (
    PatchModelV1,
    TimestampMixinV1,
    UUIDMixinV1,
    omittable,
)
from event.dto.attendance_change import AttendanceChangeDTO, AttendanceDeclareDTO


class AttendanceReadV2(FromDTOMixinV1, TimestampMixinV1, UUIDMixinV1, BaseModel):
    member_id: UUID
    participation_id: UUID
    is_attended: bool | None = Field(
        description="`null` until someone marks the place."
    )
    is_verified: bool
    comment: str | None

    model_config = ConfigDict(from_attributes=True)


class AttendanceChangeData(PatchModelV1, ToDTOMixinV1):
    __dto_cls__ = AttendanceChangeDTO

    is_attended: bool = omittable()
    comment: str | None = Field(max_length=512, default=None)
    is_verified: bool = omittable(
        description="Only the leader of the collective may set it."
    )


class AttendanceDeclareData(BaseModel, ToDTOMixinV1):
    __dto_cls__ = AttendanceDeclareDTO

    participation_id: UUID
    member_id: UUID


class ParticipationCounts(FromDTOMixinV1, BaseModel):
    id: UUID
    event_id: UUID
    collective_id: UUID
    attended_count: int
    total_count: int

    model_config = ConfigDict(from_attributes=True)


class AttendanceChanged(FromDTOMixinV1, BaseModel):
    """The place as it is now and the counters it moves, so a list can be updated
    without asking again."""

    attendance: AttendanceReadV2
    participation: ParticipationCounts

    model_config = ConfigDict(from_attributes=True)
