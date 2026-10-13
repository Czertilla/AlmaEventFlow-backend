import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from event.api.v1.schema.member import MemberRead
from event.dto.member_profile import MemberProfilePeriodDTO
from event.enum.attendance import AttendanceOutcomeEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1

MAX_PERIOD_DAYS = 731


class MemberProfileParams(BaseModel, ToDTOMixinV1):
    __dto_cls__ = MemberProfilePeriodDTO

    date_from: datetime.date | None = Field(
        default=None,
        description="First day of the period; the last 365 days when omitted.",
    )
    date_to: datetime.date | None = Field(
        default=None, description="Last day of the period; today when omitted."
    )

    @model_validator(mode="after")
    def _check_period(self) -> Self:
        if (self.date_from is None) != (self.date_to is None):
            raise ValueError("date_from and date_to go together")
        if self.date_from is not None and self.date_to is not None:
            if self.date_from > self.date_to:
                raise ValueError("date_from is after date_to")
            if (self.date_to - self.date_from).days > MAX_PERIOD_DAYS:
                raise ValueError(f"the period is longer than {MAX_PERIOD_DAYS} days")
        return self


class MemberPerson(FromDTOMixinV1, BaseModel):
    id: UUID
    surname: str
    name: str
    patronymic: str | None

    model_config = ConfigDict(from_attributes=True)


class MemberAttendanceItem(FromDTOMixinV1, BaseModel):
    attendance_id: UUID
    event_id: UUID
    event_name: str
    date: datetime.date
    status: EventStatusEnumV1
    type: EventTypeEnumV1 | None
    outcome: AttendanceOutcomeEnumV1 = Field(
        description=(
            "`attended` / `absent`: the mark was set by hand; `unmarked`: nobody "
            "marked it and the event is over; `upcoming`: the event is today "
            "(unmarked) or later."
        )
    )
    is_attended: bool | None = Field(
        description="null while the row was never marked, whatever is stored."
    )
    is_verified: bool
    comment: str | None = Field(
        description="Only for the leader, a superuser and the member themself."
    )

    model_config = ConfigDict(from_attributes=True)


class AttendanceCounts(BaseModel):
    attended: int
    absent: int
    unmarked: int
    upcoming: int

    model_config = ConfigDict(from_attributes=True)


class AttendanceByType(FromDTOMixinV1, AttendanceCounts):
    type: EventTypeEnumV1 | None


class AttendanceByMonth(FromDTOMixinV1, AttendanceCounts):
    month: datetime.date = Field(description="The first day of the month.")


class MemberAttendanceSummary(FromDTOMixinV1, AttendanceCounts):
    past: int = Field(
        description="Events already decided: attended + absent + unmarked."
    )
    verified: int = Field(description="Of those, how many the leader confirmed.")
    rate: float | None = Field(
        description="attended / past, 0..1; null while nothing is decided."
    )
    current_streak: int = Field(
        description="Attended events in a row up to the latest decided one."
    )
    longest_streak: int
    last_attended: datetime.date | None


class MemberProfileRead(FromDTOMixinV1, BaseModel):
    """Counts cover active and archived events dated inside the period."""

    member: MemberRead
    person: MemberPerson
    can_manage: bool = Field(
        description="The caller leads the collective (or is a superuser)."
    )
    date_from: datetime.date
    date_to: datetime.date
    years: list[int] = Field(
        description="Years with events of the member, newest first, any period."
    )
    summary: MemberAttendanceSummary
    by_type: list[AttendanceByType]
    by_month: list[AttendanceByMonth]
    items: list[MemberAttendanceItem] = Field(description="Newest first.")

    model_config = ConfigDict(from_attributes=True)
