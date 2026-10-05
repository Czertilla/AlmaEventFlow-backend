# pyright: reportPrivateUsage=false, reportUnknownMemberType=false
import asyncio
import logging
from collections.abc import Iterator

import pytest

from core.broker.local import MonolithBroker


@pytest.fixture
def broker() -> Iterator[MonolithBroker]:
    instance = MonolithBroker()
    before = set(instance._handlers)
    yield instance
    for topic in set(instance._handlers) - before:
        instance._handlers.pop(topic)


async def test_publish_without_subscribers_is_reported(
    broker: MonolithBroker, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        await broker.publish("payload", "tests.nobody")

    assert "no subscribers" in caplog.text
    assert "tests.nobody" in caplog.text


async def test_failing_subscriber_is_logged_with_its_topic(
    broker: MonolithBroker, caplog: pytest.LogCaptureFixture
) -> None:
    async def boom(message: str) -> None:
        raise RuntimeError("kaput")

    broker.subscriber("tests.boom")(boom)

    with caplog.at_level(logging.ERROR):
        await broker.publish("payload", "tests.boom")
        await asyncio.sleep(0.05)

    assert "tests.boom" in caplog.text
    assert "kaput" in caplog.text


async def test_dispatched_tasks_are_released_when_done(broker: MonolithBroker) -> None:
    seen: list[str] = []

    async def collect(message: str) -> None:
        seen.append(message)

    broker.subscriber("tests.collect")(collect)

    await broker.publish("payload", "tests.collect")
    await asyncio.sleep(0.05)

    assert seen == ["payload"]
    assert not broker._tasks
