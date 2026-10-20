from datetime import UTC, datetime

import pytest

from core.config.settings import settings
from event.service import notification

AWARE = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)


def test_the_creator_zone_is_used_when_the_stage_has_one() -> None:
    assert notification._format_time(AWARE, "Europe/Moscow") == "18:00"


def test_a_stage_without_a_zone_uses_the_display_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert notification._format_time(AWARE, None) == "15:00"

    monkeypatch.setattr(settings, "DISPLAY_TIMEZONE", "Europe/Moscow")

    assert notification._format_time(AWARE, None) == "18:00"
