import logging
from types import SimpleNamespace
from typing import Any

import pytest

from bot.tg.app.contextmanager import TGBotContextManager


class FakeBot:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def get_me(self) -> SimpleNamespace:
        if self.error is not None:
            raise self.error
        return SimpleNamespace(username="aef_bot", id=42)


async def test_authorised_bot_is_named_in_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    manager: Any = TGBotContextManager(bot=FakeBot(), dp=None)  # pyright: ignore[reportArgumentType]

    with caplog.at_level(logging.INFO):
        await manager.check_identity()

    assert "@aef_bot" in caplog.text


async def test_unreachable_telegram_is_reported_not_raised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    manager: Any = TGBotContextManager(
        bot=FakeBot(ConnectionError("proxy refused")),  # pyright: ignore[reportArgumentType]
        dp=None,
    )

    with caplog.at_level(logging.ERROR):
        await manager.check_identity()

    assert "getMe failed" in caplog.text
    assert "proxy refused" in caplog.text
