import os
import time
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from core.config.settings import settings
from core.utils.tz import as_aware, localize

MOSCOW = "Europe/Moscow"
AWARE = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)
NAIVE = datetime(2026, 10, 20, 15, 0)


@pytest.fixture(params=["UTC", MOSCOW, "America/New_York", "Asia/Tokyo"])
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


def test_a_naive_value_is_utc_whatever_zone_the_host_runs_in(host_zone: str) -> None:
    assert as_aware(NAIVE) == AWARE
    assert as_aware(NAIVE).timestamp() == AWARE.timestamp()
    assert localize(NAIVE, MOSCOW).strftime("%H:%M") == "18:00"


def test_an_aware_value_is_untouched_by_the_host_zone(host_zone: str) -> None:
    assert as_aware(AWARE) is AWARE
    assert localize(AWARE, MOSCOW).strftime("%H:%M") == "18:00"
    assert localize(AWARE).strftime("%H:%M") == "15:00"


@pytest.mark.parametrize("zone", [None, "", "Mars/Base", "not a zone"])
def test_without_a_usable_zone_the_value_keeps_its_own_zone(
    zone: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DISPLAY_TIMEZONE", None)

    assert localize(AWARE, zone) == AWARE
    assert localize(AWARE, zone).utcoffset() == AWARE.utcoffset()


@pytest.mark.parametrize("zone", [None, "Mars/Base"])
def test_the_display_zone_replaces_a_missing_or_unknown_stage_zone(
    zone: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "DISPLAY_TIMEZONE", MOSCOW)

    assert localize(AWARE, zone).strftime("%H:%M") == "18:00"


def test_the_stage_zone_wins_over_the_display_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DISPLAY_TIMEZONE", MOSCOW)

    assert localize(AWARE, "Asia/Yekaterinburg").strftime("%H:%M") == "20:00"


def test_an_unknown_display_zone_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "DISPLAY_TIMEZONE", "Mars/Base")

    assert localize(AWARE, None) == AWARE
