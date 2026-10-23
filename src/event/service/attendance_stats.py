import datetime
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import replace
from typing import Any
from uuid import UUID

from sqlalchemy import Row

from core.dto.base import dto_from_orm
from event.dto.attendance import AttendanceViewDTO
from event.dto.collective_profile import (
    CollectiveAttendanceSummaryDTO,
    CollectiveDayDTO,
    CollectiveEventItemDTO,
)
from event.dto.member_profile import (
    AttendanceByMonthDTO,
    AttendanceByTypeDTO,
    MemberAttendanceItemDTO,
    MemberAttendanceSummaryDTO,
)
from event.enum.attendance import AttendanceOutcomeEnumV1 as Outcome
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1
from event.models.attendance import AttendanceORM


def is_marked(edited_at: datetime.datetime | None, is_verified: bool) -> bool:
    return edited_at is not None or is_verified


def shown(
    is_attended: bool, edited_at: datetime.datetime | None, is_verified: bool
) -> bool | None:
    return is_attended if is_marked(edited_at, is_verified) else None


def shown_attendance(attendance: AttendanceORM) -> AttendanceViewDTO:
    dto = dto_from_orm(attendance, AttendanceViewDTO)
    return replace(
        dto,
        is_attended=shown(
            attendance.is_attended, attendance.edited_at, attendance.is_verified
        ),
    )


def classify(
    date: datetime.date, is_attended: bool, marked: bool, today: datetime.date
) -> Outcome:
    if date > today:
        return Outcome.upcoming
    if not marked:
        return Outcome.upcoming if date == today else Outcome.unmarked
    return Outcome.attended if is_attended else Outcome.absent


def to_item(
    row: Row[Any], today: datetime.date, show_comment: bool = False
) -> MemberAttendanceItemDTO:
    marked = is_marked(row.edited_at, row.is_verified)
    return MemberAttendanceItemDTO(
        attendance_id=row.attendance_id,
        event_id=row.event_id,
        event_name=row.event_name,
        date=row.date,
        status=EventStatusEnumV1(row.status),
        type=EventTypeEnumV1(row.type) if row.type else None,
        outcome=classify(row.date, row.is_attended, marked, today),
        is_attended=shown(row.is_attended, row.edited_at, row.is_verified),
        is_verified=row.is_verified,
        comment=row.comment if show_comment else None,
    )


def _counts(items: Sequence[MemberAttendanceItemDTO]) -> dict[str, int]:
    found = Counter(item.outcome for item in items)
    return {outcome.value: found[outcome] for outcome in Outcome}


def summarize(
    items: Sequence[MemberAttendanceItemDTO],
) -> MemberAttendanceSummaryDTO:
    counts = _counts(items)
    decided = sorted(
        (item for item in items if item.outcome is not Outcome.upcoming),
        key=lambda item: item.date,
    )
    run = longest = 0
    for item in decided:
        run = run + 1 if item.outcome is Outcome.attended else 0
        longest = max(longest, run)
    past = len(decided)
    return MemberAttendanceSummaryDTO(
        **counts,
        past=past,
        verified=sum(item.is_verified for item in decided),
        rate=counts["attended"] / past if past else None,
        current_streak=run,
        longest_streak=longest,
        last_attended=max(
            (i.date for i in decided if i.outcome is Outcome.attended),
            default=None,
        ),
    )


def by_type(
    items: Sequence[MemberAttendanceItemDTO],
) -> list[AttendanceByTypeDTO]:
    groups: defaultdict[str | None, list[MemberAttendanceItemDTO]] = defaultdict(list)
    for item in items:
        groups[item.type].append(item)
    ordered = sorted(
        groups.items(), key=lambda kv: (kv[0] is None, -len(kv[1]), kv[0] or "")
    )
    return [
        AttendanceByTypeDTO(type=group[0].type, **_counts(group))
        for _, group in ordered
    ]


def by_month(
    items: Sequence[MemberAttendanceItemDTO],
) -> list[AttendanceByMonthDTO]:
    groups: defaultdict[datetime.date, list[MemberAttendanceItemDTO]] = (
        defaultdict(list)
    )
    for item in items:
        groups[item.date.replace(day=1)].append(item)
    return [
        AttendanceByMonthDTO(month=month, **_counts(group))
        for month, group in sorted(groups.items())
    ]


def past_count(counts: dict[str, int]) -> int:
    return counts["attended"] + counts["absent"] + counts["unmarked"]


def rollup(
    items: Sequence[MemberAttendanceItemDTO],
) -> tuple[dict[str, int], int, float | None]:
    counts = _counts(items)
    past = past_count(counts)
    return counts, past, counts["attended"] / past if past else None


def summarize_collective(
    items: Sequence[MemberAttendanceItemDTO],
) -> CollectiveAttendanceSummaryDTO:
    counts, past, rate = rollup(items)
    return CollectiveAttendanceSummaryDTO(
        **counts,
        past=past,
        verified=sum(
            item.is_verified for item in items if item.outcome is not Outcome.upcoming
        ),
        rate=rate,
        events=len({item.event_id for item in items}),
    )


def by_day(items: Sequence[MemberAttendanceItemDTO]) -> list[CollectiveDayDTO]:
    groups: defaultdict[datetime.date, list[MemberAttendanceItemDTO]] = (
        defaultdict(list)
    )
    for item in items:
        groups[item.date].append(item)
    return [
        CollectiveDayDTO(date=day, **_counts(group))
        for day, group in sorted(groups.items())
    ]


def by_event(items: Sequence[MemberAttendanceItemDTO]) -> list[CollectiveEventItemDTO]:
    groups: defaultdict[UUID, list[MemberAttendanceItemDTO]] = defaultdict(list)
    for item in items:
        groups[item.event_id].append(item)
    events = [
        CollectiveEventItemDTO(
            event_id=event_id,
            event_name=group[0].event_name,
            date=group[0].date,
            status=group[0].status,
            type=group[0].type,
            **_counts(group),
        )
        for event_id, group in groups.items()
    ]
    return sorted(events, key=lambda event: (-event.date.toordinal(), event.event_name))
