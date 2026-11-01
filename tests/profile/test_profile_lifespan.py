import asyncio
from profile.app.contextmanager import ProfileContextManager
from profile.worker.outbox import NotificationOutboxPublisher

import pytest
from fastapi import FastAPI


def _running() -> bool:
    return any(task.get_name() == "profile-outbox" for task in asyncio.all_tasks())


async def test_the_lifespan_runs_the_notification_publisher_while_the_app_lives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def idle(self: NotificationOutboxPublisher) -> int:
        return 0

    monkeypatch.setattr(NotificationOutboxPublisher, "work", idle)
    manager = ProfileContextManager()

    assert not _running()
    async with manager(FastAPI()):
        assert _running()
    assert not _running()


def test_the_monolith_lifespan_starts_the_profile_publisher_too() -> None:
    from aef.app.contextmanager import AEFContextManager

    assert isinstance(AEFContextManager().profile, ProfileContextManager)
