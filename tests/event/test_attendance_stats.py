import datetime
from uuid import uuid4

import pytest

from event.dto.member_profile import MemberAttendanceItemDTO
from event.enum.attendance import AttendanceOutcomeEnumV1 as Outcome
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1
from event.service.attendance_stats import (
    by_month,
    by_type,
    classify,
    is_marked,
    shown,
    summarize,
)

TODAY = datetime.date(2026, 6, 15)


def _day(offset: int) -> datetime.date:
    return TODAY + datetime.timedelta(days=offset)


def _item(
    offset: int,
    outcome: Outcome,
    *,
    type: EventTypeEnumV1 | None = None,
    verified: bool = False,
) -> MemberAttendanceItemDTO:
    return MemberAttendanceItemDTO(
        attendance_id=uuid4(),
        event_id=uuid4(),
        event_name="Event",
        date=_day(offset),
        status=EventStatusEnumV1.active,
        type=type,
        outcome=outcome,
        is_attended=outcome is Outcome.attended,
        is_verified=verified,
        comment=None,
    )


@pytest.mark.parametrize(
    ("offset", "is_attended", "marked", "expected"),
    [
        (1, True, True, Outcome.upcoming),
        (1, False, False, Outcome.upcoming),
        (0, True, True, Outcome.attended),
        (0, False, True, Outcome.absent),
        (0, True, False, Outcome.upcoming),
        (0, False, False, Outcome.upcoming),
        (-1, True, True, Outcome.attended),
        (-1, False, True, Outcome.absent),
        (-1, False, False, Outcome.unmarked),
        (-1, True, False, Outcome.unmarked),
    ],
)
def test_an_event_is_decided_by_a_hand_set_mark_or_once_its_day_is_over(
    offset: int, is_attended: bool, marked: bool, expected: Outcome
) -> None:
    assert classify(_day(offset), is_attended, marked, TODAY) is expected


@pytest.mark.parametrize(
    ("edited", "verified", "expected"),
    [
        (False, False, False),
        (True, False, True),
        (False, True, True),
        (True, True, True),
    ],
)
def test_a_row_is_marked_once_it_was_edited_or_verified(
    edited: bool, verified: bool, expected: bool
) -> None:
    edited_at = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC) if edited else None

    assert is_marked(edited_at, verified) is expected


@pytest.mark.parametrize(
    ("stored", "edited", "verified", "expected"),
    [
        (True, False, False, None),
        (False, False, False, None),
        (True, True, False, True),
        (False, True, False, False),
        (False, False, True, False),
        (True, False, True, True),
    ],
)
def test_an_unmarked_place_shows_no_value_whatever_is_stored(
    stored: bool, edited: bool, verified: bool, expected: bool | None
) -> None:
    edited_at = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC) if edited else None

    assert shown(stored, edited_at, verified) is expected


def test_summary_counts_the_rate_and_streaks_over_decided_events() -> None:
    items = [
        _item(-60, Outcome.attended, verified=True),
        _item(-50, Outcome.attended, verified=True),
        _item(-40, Outcome.absent),
        _item(-30, Outcome.attended),
        _item(-20, Outcome.attended),
        _item(-10, Outcome.attended, verified=True),
        _item(-5, Outcome.unmarked),
        _item(2, Outcome.upcoming),
    ]

    summary = summarize(items)

    assert (summary.attended, summary.absent, summary.unmarked, summary.upcoming) == (
        5,
        1,
        1,
        1,
    )
    assert summary.past == 7
    assert summary.verified == 3
    assert summary.rate == pytest.approx(5 / 7)
    assert summary.longest_streak == 3
    assert summary.current_streak == 0
    assert summary.last_attended == _day(-10)


def test_the_current_streak_runs_up_to_the_latest_decided_event() -> None:
    items = [
        _item(-30, Outcome.absent),
        _item(-20, Outcome.attended),
        _item(-10, Outcome.attended),
        _item(3, Outcome.upcoming),
    ]

    summary = summarize(list(reversed(items)))

    assert summary.current_streak == 2
    assert summary.longest_streak == 2


def test_a_member_without_decided_events_has_no_rate() -> None:
    summary = summarize([_item(4, Outcome.upcoming)])

    assert summary.rate is None
    assert summary.past == 0
    assert summary.last_attended is None
    assert summarize([]).upcoming == 0


def test_types_are_ordered_by_size_with_the_untyped_last() -> None:
    items = [
        _item(-3, Outcome.attended, type=EventTypeEnumV1.concert),
        _item(-2, Outcome.absent, type=EventTypeEnumV1.rehearsal),
        _item(-1, Outcome.attended, type=EventTypeEnumV1.rehearsal),
        _item(-4, Outcome.attended),
        _item(-5, Outcome.attended),
        _item(-6, Outcome.attended),
    ]

    result = by_type(items)

    assert [group.type for group in result] == [
        EventTypeEnumV1.rehearsal,
        EventTypeEnumV1.concert,
        None,
    ]
    assert (result[0].attended, result[0].absent) == (1, 1)
    assert result[2].attended == 3


def test_months_are_grouped_by_their_first_day_in_order() -> None:
    items = [
        _item(0, Outcome.attended),
        _item(-1, Outcome.absent),
        _item(-31, Outcome.attended),
        _item(40, Outcome.upcoming),
    ]

    result = by_month(items)

    assert [group.month for group in result] == [
        datetime.date(2026, 5, 1),
        datetime.date(2026, 6, 1),
        datetime.date(2026, 7, 1),
    ]
    assert [(g.attended, g.absent, g.upcoming) for g in result] == [
        (1, 0, 0),
        (1, 1, 0),
        (0, 0, 1),
    ]
