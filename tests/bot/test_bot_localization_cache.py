import logging
from typing import Any

import pytest

from bot.tg.text.localization import i18n_manager


class BrokenCache:
    async def get(self, *args: Any, **kwargs: Any) -> None:
        raise ConnectionError("redis is down")

    async def set(self, *args: Any, **kwargs: Any) -> None:
        raise ConnectionError("redis is down")


async def test_translation_survives_an_unreachable_cache(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(i18n_manager, "cache", BrokenCache())

    with caplog.at_level(logging.WARNING):
        text = await i18n_manager.get("announcement.cta", lang="en")

    assert "attendance" in text
    assert "redis is down" in caplog.text
