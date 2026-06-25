from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date
from logging import getLogger
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import settings
from core.enum.notify import NotificationCategory
from core.schema.message.notify import NotificationRequest
from core.utils.notify import send_notification

from event.models.attendance import AttendanceORM
from event.models.event import EventORM, EventStatusORM
from event.models.member import MemberORM
from event.models.participation import ParticipationORM

logger = getLogger(__name__)


def is_trigger_status(status: str | None) -> bool:
    """Whether an event status spawns attendance notifications."""
    return status is not None and status in settings.EVENT_NOTIFY_TRIGGER_STATUSES


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
    for request in _build_requests(rows):
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


def _build_requests(rows: Sequence) -> list[NotificationRequest]:
    names: dict[UUID, str] = {}
    dates: dict[UUID, date | None] = {}
    persons: dict[UUID, set[UUID]] = defaultdict(set)
    for event_id, name, event_date, person_id in rows:
        names[event_id] = name
        dates[event_id] = event_date
        persons[event_id].add(person_id)
    return [
        _build_request(event_id, names[event_id], dates[event_id], person_ids)
        for event_id, person_ids in persons.items()
    ]


def _build_request(
    event_id: UUID,
    name: str,
    event_date: date | None,
    person_ids: set[UUID],
) -> NotificationRequest:
    action_url = f"{settings.FRONTEND_URL}/event/{event_id}"
    data = {
        "event_id": str(event_id),
        "event_name": name,
        "action_url": action_url,
    }
    if event_date is not None:
        data["event_date"] = event_date.isoformat()
    return NotificationRequest(
        person_ids=list(person_ids),
        category=NotificationCategory.attendance,
        title="Новое мероприятие",
        body=f"Вас отметили в мероприятии «{name}». Подтвердите участие.",
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
