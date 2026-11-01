import json
from datetime import UTC, datetime, timedelta
from profile.service.outbox import NotificationOutboxService
from profile.uow.visibility import OutboxUOW
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.config.settings import settings
from core.enum.notify import NotificationCategory
from core.schema.message.notify import NotificationRequest

Maker = async_sessionmaker[AsyncSession]


class Sender:
    def __init__(self) -> None:
        self.sent: list[NotificationRequest] = []
        self.failing: set[UUID] = set()

    async def __call__(self, request: NotificationRequest) -> None:
        if request.event_id in self.failing:
            raise ConnectionError("notify is away")
        self.sent.append(request)


async def _row(
    engine: AsyncEngine,
    person_id: UUID,
    *,
    due_in: timedelta = timedelta(0),
    attempts: int = 0,
    status: str = "pending",
    title: str = "Видимость данных расширена",
) -> UUID:
    row_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO notification_outbox (id, person_id, category, title, "
                "body, data, status, attempts, next_attempt_at, created_at) VALUES "
                "(:id, :person, 'system', :title, 'Поле «ФИО» теперь видно всем.', "
                "CAST(:data AS jsonb), :status, :attempts, :due, now())"
            ),
            {
                "id": row_id,
                "person": person_id,
                "title": title,
                "data": json.dumps({"kind": "visibility_widened", "field": "x"}),
                "status": status,
                "attempts": attempts,
                "due": datetime.now(UTC) + due_in,
            },
        )
    return row_id


async def _state(engine: AsyncEngine, row_id: UUID) -> tuple[str, int, datetime]:
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT status, attempts, next_attempt_at "
                    "FROM notification_outbox WHERE id = :id"
                ),
                {"id": row_id},
            )
        ).one()
    return row.status, row.attempts, row.next_attempt_at


def _service(maker: Maker, sender: Sender) -> NotificationOutboxService:
    return NotificationOutboxService(OutboxUOW(maker), sender)


async def test_due_notifications_are_handed_to_notify_once(
    profile_engine: AsyncEngine, profile_sessionmaker: Maker
) -> None:
    person_id = uuid4()
    first = await _row(profile_engine, person_id)
    second = await _row(profile_engine, person_id)
    later = await _row(profile_engine, person_id, due_in=timedelta(hours=1))
    sender = Sender()
    service = _service(profile_sessionmaker, sender)

    published = await service.publish_batch()
    again = await service.publish_batch()

    assert (published, again) == (2, 0)
    assert {request.event_id for request in sender.sent} == {first, second}
    request = sender.sent[0]
    assert request.person_ids == [person_id]
    assert request.user_ids == []
    assert request.category == NotificationCategory.system
    assert request.title == "Видимость данных расширена"
    assert request.data == {"kind": "visibility_widened", "field": "x"}
    assert (await _state(profile_engine, first))[0] == "published"
    assert (await _state(profile_engine, later))[0] == "pending"


async def test_a_failed_hand_over_waits_and_is_retried_later(
    profile_engine: AsyncEngine, profile_sessionmaker: Maker
) -> None:
    row_id = await _row(profile_engine, uuid4())
    sender = Sender()
    sender.failing.add(row_id)
    service = _service(profile_sessionmaker, sender)
    before = datetime.now(UTC)

    published = await service.publish_batch()
    status, attempts, next_attempt = await _state(profile_engine, row_id)
    waiting = await service.publish_batch()

    assert published == waiting == 0
    assert (status, attempts) == ("pending", 1)
    assert next_attempt >= before + timedelta(
        seconds=settings.PROFILE_OUTBOX_RETRY_BASE_SECONDS - 1
    )
    sender.failing.clear()
    assert sender.sent == []


async def test_the_delay_doubles_with_every_failure(
    profile_engine: AsyncEngine, profile_sessionmaker: Maker
) -> None:
    row_id = await _row(profile_engine, uuid4(), attempts=2)
    sender = Sender()
    sender.failing.add(row_id)
    before = datetime.now(UTC)

    await _service(profile_sessionmaker, sender).publish_batch()
    _, attempts, next_attempt = await _state(profile_engine, row_id)

    assert attempts == 3
    assert next_attempt >= before + timedelta(
        seconds=settings.PROFILE_OUTBOX_RETRY_BASE_SECONDS * 4 - 1
    )


async def test_a_notification_that_keeps_failing_is_given_up(
    profile_engine: AsyncEngine,
    profile_sessionmaker: Maker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "PROFILE_OUTBOX_MAX_ATTEMPTS", 2)
    row_id = await _row(profile_engine, uuid4(), attempts=1)
    sender = Sender()
    sender.failing.add(row_id)

    await _service(profile_sessionmaker, sender).publish_batch()

    status, attempts, _ = await _state(profile_engine, row_id)
    assert (status, attempts) == ("dead", 2)


async def test_one_failure_does_not_hold_the_others_back(
    profile_engine: AsyncEngine, profile_sessionmaker: Maker
) -> None:
    broken = await _row(profile_engine, uuid4())
    fine = await _row(profile_engine, uuid4())
    sender = Sender()
    sender.failing.add(broken)

    published = await _service(profile_sessionmaker, sender).publish_batch()

    assert published == 1
    assert [request.event_id for request in sender.sent] == [fine]
    assert (await _state(profile_engine, fine))[0] == "published"
    assert (await _state(profile_engine, broken))[0] == "pending"


async def test_a_published_or_dead_notification_is_not_sent_again(
    profile_engine: AsyncEngine, profile_sessionmaker: Maker
) -> None:
    await _row(profile_engine, uuid4(), status="published")
    await _row(profile_engine, uuid4(), status="dead", attempts=8)
    sender = Sender()

    published = await _service(profile_sessionmaker, sender).publish_batch()

    assert published == 0
    assert sender.sent == []
