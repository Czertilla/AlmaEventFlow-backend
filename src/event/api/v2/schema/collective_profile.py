import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1
from event.api.v2.schema.member_profile import (
    AttendanceByMonth,
    AttendanceByType,
    AttendanceCounts,
    MemberPerson,
)
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


class CollectiveInfo(FromDTOMixinV1, BaseModel):
    id: UUID
    name: str
    is_verified: bool
    principal: MemberPerson | None
    active_members: int

    model_config = ConfigDict(from_attributes=True)


class CollectiveAttendanceSummary(FromDTOMixinV1, AttendanceCounts):
    past: int = Field(
        description=(
            "Declared places of events already decided: attended + absent + unmarked."
        )
    )
    verified: int = Field(description="Of those, how many the leader confirmed.")
    rate: float | None = Field(
        description="attended / past, 0..1; null while nothing is decided."
    )
    events: int = Field(description="Events of the collective inside the period.")


class CollectiveDay(FromDTOMixinV1, AttendanceCounts):
    date: datetime.date


class CollectiveEventItem(FromDTOMixinV1, AttendanceCounts):
    event_id: UUID
    event_name: str
    date: datetime.date
    status: EventStatusEnumV1
    type: EventTypeEnumV1 | None


class CollectiveMemberItem(FromDTOMixinV1, AttendanceCounts):
    member_id: UUID
    person: MemberPerson
    is_active: bool
    past: int = Field(description="attended + absent + unmarked of the member.")
    rate: float | None = Field(description="attended / past, 0..1.")


class CollectiveProfileRead(FromDTOMixinV1, BaseModel):
    """Counts cover the places declared (attendance rows) for the collective's
    active and archived events dated inside the period."""

    collective: CollectiveInfo
    can_manage: bool = Field(
        description="The caller leads the collective (or is a superuser)."
    )
    date_from: datetime.date
    date_to: datetime.date
    years: list[int] = Field(
        description="Years with events of the collective, newest first, any period."
    )
    summary: CollectiveAttendanceSummary
    by_type: list[AttendanceByType]
    by_month: list[AttendanceByMonth]
    days: list[CollectiveDay] = Field(
        description="One entry per day with events, oldest first."
    )
    events: list[CollectiveEventItem] = Field(description="Newest first.")
    members: list[CollectiveMemberItem] = Field(
        description=("Active members and those with events in the period, by surname.")
    )

    model_config = ConfigDict(from_attributes=True)
