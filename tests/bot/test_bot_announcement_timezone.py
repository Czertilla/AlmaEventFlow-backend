import os
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from bot.tg.service import announcement
from core.config.settings import settings

AWARE = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
NAIVE = datetime(2026, 10, 20, 15, 0)


@pytest.fixture(params=["UTC", "Europe/Moscow", "America/New_York"])
def host_zone(request: pytest.FixtureRequest) -> Iterator[str]:
    previous = os.environ.get("TZ")
    os.environ["TZ"] = request.param
    time.tzset()
    yield request.param
    if previous is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = previous
    time.tzset()


def test_the_text_and_the_entity_do_not_depend_on_the_host_zone(host_zone: str) -> None:
    for value in (AWARE, NAIVE):
        assert announcement._format_time(value, "Europe/Moscow") == "18:00"
        entity = announcement._tg_time(value, "t", "x")
        assert f'unix="{int(AWARE.timestamp())}"' in entity


def test_a_stage_without_a_zone_uses_the_display_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert announcement._format_time(AWARE, None) == "15:00"

    monkeypatch.setattr(settings, "DISPLAY_TIMEZONE", "Europe/Moscow")

    assert announcement._format_time(AWARE, None) == "18:00"
