from typing import Any, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, Update

from bot.tg.text.builder import TextBuilder
from bot.tg.utils.mixins.middleware import (
    GetMessageMixin,
    GetUserMixin,
    HandlerMixin,
    LoggerMiddlewareMixin,
)


class UsernameWarningMiddleware(
    BaseMiddleware,
    LoggerMiddlewareMixin,
    GetMessageMixin,
    HandlerMixin,
    GetUserMixin,
):
    def __init__(
        self, router_name: str = "username_warning_middleware"
    ) -> None:
        super().__init__(router_name)

    async def __call__(
        self,
        handler: Callable,
        update: Update,
        data: dict[str, Any],
    ) -> object:
        user = self.get_user(data)
        if user.username is None:
            text_builder: TextBuilder = data.get(
                "text_builder",
                TextBuilder(user.language_code),
            )
            if isinstance(update.event, (Message, CallbackQuery)):
                await update.event.answer(
                    await text_builder.get_username_warning()
                )
        return await handler(update, data)
