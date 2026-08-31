from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, datetime
from logging import getLogger
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import settings
from core.enum.notify import NotificationCategory
from core.schema.message.announcement import AnnouncementRequest, AnnouncementStage
from core.schema.message.notify import NotificationRequest
from core.utils.announcement import send_announcement
from core.utils.notify import send_notification
from event.models.attendance import AttendanceORM
from event.models.event import EventORM, EventStatusORM
from event.models.location import LocationORM
from event.models.member import MemberORM
from event.models.organization import OrganizationORM
from event.models.participation import ParticipationORM
from event.models.stage import EventStageORM

logger = getLogger(__name__)

_MONTHS_RU_GENITIVE = (
    "",
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

StageInfo = tuple[str, datetime, datetime | None, str | None, str | None]
"""(name, start_at, end_at, timezone, description) per event stage, ordered by
start_at. ``timezone`` is the IANA zone name of the client that created the
stage -- ``start_at``/``end_at`` are absolute UTC instants, correct for every
consumer, but only this field lets a fixed-zone display (Telegram's plain
text) show the time the creator actually meant."""


def is_trigger_status(status: str | None) -> bool:
    """Whether an event status spawns attendance notifications."""
    return status is not None and status in settings.EVENT_NOTIFY_TRIGGER_STATUSES


def _format_date(value: date) -> str:
    return f"{value.day} {_MONTHS_RU_GENITIVE[value.month]} {value.year}"


def _format_time(value: datetime, tz_name: str | None = None) -> str:
    """Renders the wall-clock time in ``tz_name`` when given and valid --
    falling back to whatever zone ``value`` already carries (the DB session's,
    for a stage with no recorded creator zone) otherwise."""
    if tz_name:
        try:
            value = value.astimezone(ZoneInfo(tz_name))
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return value.strftime("%H:%M")


def _format_date_time(
    event_date: date | None,
    stage_start: datetime | None,
    stage_tz: str | None = None,
) -> str:
    """Renders the event date, plus the earliest stage's start time when
    known -- ``EventORM.date`` itself carries no time, only stages do."""
    if event_date is None:
        return ""
    text = _format_date(event_date)
    if stage_start is not None:
        text += f", {_format_time(stage_start, stage_tz)}"
    return text


async def notify_event_targets(
    uow,
    *,
    attendance_ids: Iterable[UUID] | None = None,
    participation_ids: Iterable[UUID] | None = None,
    event_ids: Iterable[UUID] | None = None,
) -> None:
    """Resolves the persons attached to attendances of trigger-status events in
    the given scope and publishes one attendance notification per event. Must be
    called inside an open unit of work (uses its session); publish is best-effort
    and never raises into the caller."""
    rows = await _resolve_targets(
        uow.session,
        attendance_ids=attendance_ids,
        participation_ids=participation_ids,
        event_ids=event_ids,
    )
    stages = await _resolve_stages(uow.session, {row[0] for row in rows})
    for request in _build_requests(rows, stages):
        await _publish(request)


async def _resolve_targets(
    session: AsyncSession,
    *,
    attendance_ids: Iterable[UUID] | None,
    participation_ids: Iterable[UUID] | None,
    event_ids: Iterable[UUID] | None,
) -> Sequence:
    stmt = (
        select(
            EventORM.id, EventORM.name, EventORM.date, MemberORM.person_id
        )
        .select_from(AttendanceORM)
        .join(
            ParticipationORM,
            AttendanceORM.participation_id == ParticipationORM.id,
        )
        .join(EventORM, EventORM.id == ParticipationORM.event_id)
        .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
        .join(MemberORM, MemberORM.id == AttendanceORM.member_id)
        .where(
            EventStatusORM.name.in_(settings.EVENT_NOTIFY_TRIGGER_STATUSES)
        )
    )
    if attendance_ids is not None:
        stmt = stmt.where(AttendanceORM.id.in_(list(attendance_ids)))
    if participation_ids is not None:
        stmt = stmt.where(
            AttendanceORM.participation_id.in_(list(participation_ids))
        )
    if event_ids is not None:
        stmt = stmt.where(ParticipationORM.event_id.in_(list(event_ids)))
    return (await session.execute(stmt)).all()


async def _resolve_stages(
    session: AsyncSession, event_ids: Iterable[UUID]
) -> dict[UUID, list[StageInfo]]:
    event_ids = list(event_ids)
    if not event_ids:
        return {}
    stmt = (
        select(
            EventStageORM.event_id,
            EventStageORM.name,
            EventStageORM.start_at,
            EventStageORM.end_at,
            EventStageORM.timezone,
            EventStageORM.description,
        )
        .where(EventStageORM.event_id.in_(event_ids))
        .order_by(EventStageORM.event_id, EventStageORM.start_at)
    )
    grouped: dict[UUID, list[StageInfo]] = defaultdict(list)
    for event_id, name, start_at, end_at, tz_name, description in (
        await session.execute(stmt)
    ).all():
        grouped[event_id].append((name, start_at, end_at, tz_name, description))
    return grouped


def _build_requests(
    rows: Sequence, stages: dict[UUID, list[StageInfo]]
) -> list[NotificationRequest]:
    names: dict[UUID, str] = {}
    dates: dict[UUID, date | None] = {}
    persons: dict[UUID, set[UUID]] = defaultdict(set)
    for event_id, name, event_date, person_id in rows:
        names[event_id] = name
        dates[event_id] = event_date
        persons[event_id].add(person_id)
    return [
        _build_request(
            event_id,
            names[event_id],
            dates[event_id],
            stages.get(event_id, [None])[0],
            person_ids,
        )
        for event_id, person_ids in persons.items()
    ]


def _build_request(
    event_id: UUID,
    name: str,
    event_date: date | None,
    earliest_stage: StageInfo | None,
    person_ids: set[UUID],
) -> NotificationRequest:
    action_url = f"{settings.FRONTEND_URL}/event/{event_id}"
    stage_start = earliest_stage[1] if earliest_stage else None
    stage_tz = earliest_stage[3] if earliest_stage else None
    body = f"Вас отметили в мероприятии «{name}». Подтвердите участие."
    date_time = _format_date_time(event_date, stage_start, stage_tz)
    if date_time:
        body += f"\n📅 {date_time}"
    data = {
        "event_id": str(event_id),
        "event_name": name,
        "action_url": action_url,
    }
    if event_date is not None:
        data["event_date"] = event_date.isoformat()
    if stage_start is not None:
        # Raw UTC instant (+ the creator's zone, when known) so any other
        # client can render in whichever zone it prefers -- the Telegram
        # text above already committed to the creator's own zone, since it
        # has no per-viewer rendering to fall back on.
        data["stage_start_at"] = stage_start.isoformat()
        if stage_tz:
            data["stage_timezone"] = stage_tz
    return NotificationRequest(
        person_ids=list(person_ids),
        category=NotificationCategory.attendance,
        title="Новое мероприятие",
        body=body,
        action_url=action_url,
        data=data,
    )


async def _publish(request: NotificationRequest) -> None:
    try:
        await send_notification(request)
    except Exception:
        logger.exception(
            "Failed to publish attendance notification for event %s",
            request.data.get("event_id"),
        )


async def notify_collective_chats(
    uow, *, event_ids: Iterable[UUID]
) -> None:
    """Announces a trigger-status event to each participating collective's
    official chat (a separate, non-personal pipeline from
    ``notify_event_targets`` — see ``src/notify/TECH_TASK.md`` §5.3). ``bot``
    resolves collective_id -> chat_id and owns edit-vs-send by event_id; a
    collective with no chat set up is simply skipped there. Best-effort,
    like the personal pipeline."""
    rows = await _resolve_collective_targets(uow.session, event_ids=event_ids)
    stages = await _resolve_stages(uow.session, {row[0] for row in rows})
    for request in _build_announcements(rows, stages):
        await _publish_announcement(request)


async def _resolve_collective_targets(
    session: AsyncSession, *, event_ids: Iterable[UUID]
) -> Sequence:
    stmt = (
        select(
            EventORM.id,
            EventORM.name,
            EventORM.date,
            EventORM.description,
            LocationORM.name,
            OrganizationORM.name,
            ParticipationORM.collective_id,
        )
        .select_from(ParticipationORM)
        .join(EventORM, EventORM.id == ParticipationORM.event_id)
        .join(EventStatusORM, EventStatusORM.id == EventORM.status_id)
        .outerjoin(LocationORM, LocationORM.id == EventORM.location_id)
        .outerjoin(OrganizationORM, OrganizationORM.id == EventORM.organizer_id)
        .where(
            EventStatusORM.name.in_(settings.EVENT_NOTIFY_TRIGGER_STATUSES),
            ParticipationORM.event_id.in_(list(event_ids)),
        )
    )
    return (await session.execute(stmt)).all()


def _build_announcements(
    rows: Sequence, stages: dict[UUID, list[StageInfo]]
) -> list[AnnouncementRequest]:
    result = []
    for row in rows:
        (
            event_id,
            name,
            event_date,
            description,
            location,
            organizer,
            collective_id,
        ) = row
        result.append(
            _build_announcement(
                event_id,
                name,
                event_date,
                description,
                location,
                organizer,
                collective_id,
                stages.get(event_id, []),
            )
        )
    return result


def _build_announcement(
    event_id: UUID,
    name: str,
    event_date: date | None,
    description: str | None,
    location: str | None,
    organizer: str | None,
    collective_id: UUID,
    stages: list[StageInfo],
) -> AnnouncementRequest:
    return AnnouncementRequest(
        collective_id=collective_id,
        event_id=event_id,
        event_name=name,
        event_date=event_date,
        event_description=description,
        location=location,
        organizer=organizer,
        stages=[
            AnnouncementStage(
                name=stage_name,
                start_at=start_at,
                end_at=end_at,
                description=stage_description,
                timezone=tz_name,
            )
            for stage_name, start_at, end_at, tz_name, stage_description in stages
        ],
        action_url=f"{settings.FRONTEND_URL}/event/{event_id}",
    )


async def _publish_announcement(request: AnnouncementRequest) -> None:
    try:
        await send_announcement(request)
    except Exception:
        logger.exception(
            "Failed to publish announcement for event %s, collective %s",
            request.event_id,
            request.collective_id,
        )
