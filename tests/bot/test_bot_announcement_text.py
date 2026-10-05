from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from aiocache import SimpleMemoryCache  # pyright: ignore[reportMissingTypeStubs]

from bot.tg.service.announcement import build_announcement_text
from bot.tg.text.localization import i18n_manager
from core.schema.message.announcement import AnnouncementRequest, AnnouncementStage

TELEGRAM_LIMIT = 4096


@pytest.fixture(autouse=True)
def memory_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(i18n_manager, "cache", SimpleMemoryCache())


def _request(**overrides: object) -> AnnouncementRequest:
    fields: dict[str, object] = {
        "collective_id": uuid4(),
        "event_id": uuid4(),
        "event_name": "Concert",
        "event_date": date(2026, 5, 1),
        "action_url": "https://example.test/event/1",
    }
    fields.update(overrides)
    return AnnouncementRequest(**fields)  # pyright: ignore[reportArgumentType]


def _stages(count: int, description: int) -> list[AnnouncementStage]:
    return [
        AnnouncementStage(
            name=f"Stage {number} " + "S" * 150,
            start_at=datetime(2026, 5, 1, 9, tzinfo=UTC),
            end_at=datetime(2026, 5, 1, 10, tzinfo=UTC),
            description="x" * description,
        )
        for number in range(count)
    ]


async def test_short_announcement_keeps_everything() -> None:
    text = await build_announcement_text(
        _request(event_description="Bring a friend", stages=_stages(2, 20)), lang="ru"
    )

    assert "Bring a friend" in text
    assert text.count("Stage") == 2


async def test_oversized_announcement_fits_the_telegram_limit() -> None:
    request = _request(
        event_name="N" * 300,
        event_description="d" * 10_000,
        location="L" * 500,
        organizer="O" * 500,
        stages=_stages(40, 500),
    )

    text = await build_announcement_text(request, lang="ru")

    assert len(text) <= TELEGRAM_LIMIT


async def test_trimmed_announcement_keeps_markup_and_call_to_action() -> None:
    request = _request(event_description="d" * 10_000, stages=_stages(40, 500))

    text = await build_announcement_text(request, lang="ru")

    for tag in ("b", "a", "i"):
        opened = text.count(f"<{tag}>") + text.count(f"<{tag} ")
        assert opened == text.count(f"</{tag}>")
    assert text.endswith(await i18n_manager.get("announcement.cta", lang="ru"))


async def test_escaped_symbols_do_not_overflow_the_limit() -> None:
    request = _request(
        event_name="&" * 300,
        event_description="<" * 10_000,
        location="&" * 500,
        organizer="&" * 500,
        stages=_stages(40, 500),
    )

    text = await build_announcement_text(request, lang="ru")

    assert len(text) <= TELEGRAM_LIMIT
