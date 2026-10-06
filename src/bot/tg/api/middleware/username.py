from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message, Update

from bot.tg.schema.user import TGUser
from bot.tg.text.builder import TextBuilder
from bot.tg.utils.mixins.middleware import (
    GetMessageMixin,
    GetUserMixin,
    HandlerMixin,
    LoggerMiddlewareMixin,
)
from core.dependencies.redis import redis

HINT_INTERVAL_SECONDS = 7 * 24 * 3600


def hint_key(tgid: int) -> str:
    return f"tg:hint:username:{tgid}"


class UsernameWarningMiddleware(
    BaseMiddleware,
    LoggerMiddlewareMixin,
    GetMessageMixin,
    HandlerMixin,
    GetUserMixin,
):
    """Nudges a user without a ``@username`` once a week, in private chat only,
    after the real answer has been sent."""

    def __init__(
        self, router_name: str = "username_warning_middleware"
    ) -> None:
        super().__init__(router_name)

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        update: Update,
        data: dict[str, Any],
    ) -> object:
        result: object = await handler(update, data)
        user = data.get("user")
        event = update.message
        if (
            isinstance(user, TGUser)
            and user.username is None
            and isinstance(event, Message)
            and event.chat.type == ChatType.PRIVATE
            and await self._claim(user.id)
        ):
            text_builder = data.get("text_builder") or TextBuilder(
                user.language_code
            )
            await event.answer(await text_builder.get_username_warning())
        return result

    async def _claim(self, tgid: int) -> bool:
        try:
            return bool(
                await redis.set(
                    hint_key(tgid), 1, nx=True, ex=HINT_INTERVAL_SECONDS
                )
            )
        except Exception:
            self.logger.warning("username hint throttle unavailable", exc_info=True)
            return False
