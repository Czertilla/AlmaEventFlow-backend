import datetime
from collections import Counter, defaultdict
from collections.abc import Sequence

from event.dto.member_profile import (
    AttendanceByMonthDTO,
    AttendanceByTypeDTO,
    MemberAttendanceItemDTO,
    MemberAttendanceSummaryDTO,
)
from event.enum.attendance import AttendanceOutcomeEnumV1 as Outcome


def is_marked(
    is_attended: bool | None, edited_at: datetime.datetime | None, is_verified: bool
) -> bool:
    return is_attended is not None and (edited_at is not None or is_verified)


def classify(
    date: datetime.date, is_attended: bool | None, marked: bool, today: datetime.date
) -> Outcome:
    if date > today:
        return Outcome.upcoming
    if not marked:
        return Outcome.upcoming if date == today else Outcome.unmarked
    return Outcome.attended if is_attended else Outcome.absent


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
