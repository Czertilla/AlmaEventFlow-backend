from collections.abc import Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Update, User

from bot.tg.service.user import TelegramUserService as UserService
from bot.tg.uow.user import UserUOW
from bot.tg.utils.mixins.middleware import (
    GetMessageMixin,
    GetUserMixin,
    HandlerMixin,
    LoggerMiddlewareMixin,
)


class UserUpdateMiddleware(
    BaseMiddleware,
    LoggerMiddlewareMixin,
    GetMessageMixin,
    HandlerMixin,
    GetUserMixin,
):
    def __init__(self, router_name: str = "user_update_middleware") -> None:
        super().__init__(router_name)

    async def __call__(
        self,
        handler: Callable,
        update: Update,
        data: dict[str, Any],
    ) -> object:
        sender = data.get("event_from_user")
        data["user"] = (
            await UserService(UserUOW()).update_user(sender)
            if isinstance(sender, User) and not sender.is_bot
            else None
        )
        return await handler(update, data)
