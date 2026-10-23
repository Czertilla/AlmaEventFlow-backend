import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1
from event.api.v1.schema.role import RolePreview
from event.api.v1.schema.stage import StageRead
from event.api.v2.schema.attendance import AttendanceReadV2
from event.api.v2.schema.feed import EventPlace
from event.api.v2.schema.member_profile import MemberPerson
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.priority import EventPriorityEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


class RosterMember(FromDTOMixinV1, BaseModel):
    id: UUID
    person: MemberPerson
    is_active: bool
    roles: list[RolePreview]

    model_config = ConfigDict(from_attributes=True)


class PageEvent(FromDTOMixinV1, BaseModel):
    id: UUID
    name: str
    date: datetime.date | None
    description: str | None
    status: EventStatusEnumV1
    level: EventLevelEnumV1 | None
    type: EventTypeEnumV1 | None
    format: EventFormatEnumV1
    organizer_id: UUID | None
    location_id: UUID | None
    location: EventPlace | None = Field(
        description="The text to show and the point on the map; geo has the rest."
    )
    created_at: datetime.datetime
    edited_at: datetime.datetime | None

    model_config = ConfigDict(from_attributes=True)


class PageAttendance(AttendanceReadV2):
    member: RosterMember


class PageParticipation(FromDTOMixinV1, BaseModel):
    id: UUID
    collective_id: UUID
    collective_name: str
    priority_degree: EventPriorityEnumV1 | None
    is_principal: bool = Field(
        description="The caller leads the collective (or is a superuser)."
    )
    is_member: bool = Field(
        description="The caller has a membership in the collective."
    )
    can_view_attendances: bool = Field(
        description="Only the leader and the members see the places."
    )
    attended_count: int | None = Field(
        description="Null unless the places are visible."
    )
    total_count: int | None
    my_attendance_id: UUID | None
    attendances: list[PageAttendance] = Field(
        description="By surname; empty unless visible."
    )
    addable_members: list[RosterMember] = Field(
        description="Active members without a place yet; for the leader only."
    )

    model_config = ConfigDict(from_attributes=True)


class EventPageRead(FromDTOMixinV1, BaseModel):
    """Everything the page of an event shows. Collectives are the participating ones,
    the caller's own first, then by name."""

    event: PageEvent
    stages: list[StageRead] = Field(description="By start.")
    participations: list[PageParticipation]
    editable_collective_id: UUID | None = Field(
        description="The collective the caller edits the event on behalf of, if any."
    )

    model_config = ConfigDict(from_attributes=True)
