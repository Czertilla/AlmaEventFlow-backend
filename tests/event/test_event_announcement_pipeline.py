# pyright: reportUnknownVariableType=false
import logging
from datetime import date
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from core.schema.message.announcement import AnnouncementRequest
from event.service import notification
from event.service.notification import (
    notify_collective_chats,
    notify_event_targets,
)


class BrokenSession:
    async def execute(self, *args: Any, **kwargs: Any) -> None:
        raise RuntimeError("database is down")


def _no_session() -> Any:
    return SimpleNamespace(session=None)


def _broken_uow() -> Any:
    return SimpleNamespace(session=BrokenSession())


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch) -> list[AnnouncementRequest]:
    sent: list[AnnouncementRequest] = []

    async def record(request: AnnouncementRequest) -> None:
        sent.append(request)

    monkeypatch.setattr(notification, "send_announcement", record)
    return sent


def _patch_targets(
    monkeypatch: pytest.MonkeyPatch, rows: list[tuple[Any, ...]]
) -> None:
    async def targets(session: Any, *, event_ids: Any) -> list[tuple[Any, ...]]:
        return rows

    async def stages(session: Any, event_ids: Any) -> dict[UUID, list[Any]]:
        return {}

    monkeypatch.setattr(notification, "_resolve_collective_targets", targets)
    monkeypatch.setattr(notification, "_resolve_stages", stages)


async def test_collective_resolution_failure_never_reaches_the_caller(
    caplog: pytest.LogCaptureFixture,
) -> None:
    event_id = uuid4()

    with caplog.at_level(logging.INFO):
        await notify_collective_chats(_broken_uow(), event_ids=[event_id])

    assert str(event_id) in caplog.text
    assert "database is down" in caplog.text


async def test_attendance_resolution_failure_never_reaches_the_caller(
    caplog: pytest.LogCaptureFixture,
) -> None:
    event_id = uuid4()

    with caplog.at_level(logging.INFO):
        await notify_event_targets(_broken_uow(), event_ids=[event_id])

    assert str(event_id) in caplog.text
    assert "database is down" in caplog.text


async def test_event_without_participating_collective_is_explained(
    monkeypatch: pytest.MonkeyPatch,
    published: list[AnnouncementRequest],
    caplog: pytest.LogCaptureFixture,
) -> None:
    event_id = uuid4()
    _patch_targets(monkeypatch, [])

    with caplog.at_level(logging.INFO):
        await notify_collective_chats(_no_session(), event_ids=[event_id])

    assert not published
    assert str(event_id) in caplog.text
    assert "no announcement targets" in caplog.text


async def test_each_participating_collective_gets_one_published_request(
    monkeypatch: pytest.MonkeyPatch,
    published: list[AnnouncementRequest],
    caplog: pytest.LogCaptureFixture,
) -> None:
    event_id, first, second = uuid4(), uuid4(), uuid4()
    _patch_targets(
        monkeypatch,
        [
            (event_id, "Concert", date(2026, 5, 1), None, None, None, first),
            (event_id, "Concert", date(2026, 5, 1), None, None, None, second),
        ],
    )

    with caplog.at_level(logging.INFO):
        await notify_collective_chats(_no_session(), event_ids=[event_id])

    assert {request.collective_id for request in published} == {first, second}
    assert str(first) in caplog.text
    assert str(second) in caplog.text


async def test_publish_failure_is_logged_with_its_context(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    event_id, collective_id = uuid4(), uuid4()
    _patch_targets(
        monkeypatch,
        [(event_id, "Concert", None, None, None, None, collective_id)],
    )

    async def broken(request: AnnouncementRequest) -> None:
        raise ConnectionError("kafka is unreachable")

    monkeypatch.setattr(notification, "send_announcement", broken)

    with caplog.at_level(logging.INFO):
        await notify_collective_chats(_no_session(), event_ids=[event_id])

    assert str(event_id) in caplog.text
    assert str(collective_id) in caplog.text
    assert "kafka is unreachable" in caplog.text
