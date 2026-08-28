from typing import Any, Callable

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
        self.logger.debug(f"updating user by {update=}")
        user = self.get_user(data)
        if isinstance(user, User):
            self.logger.debug(f"updating user {user.id=}")
            user_service = UserService(UserUOW())
            updated_user = await user_service.update_user(user, update)
            if not updated_user:
                self.logger.debug(f"user {user.id=} not updated")
                return
            self.logger.info(f"updated user {updated_user.id=}")
            data["user"] = updated_user
        return await handler(update, data)
