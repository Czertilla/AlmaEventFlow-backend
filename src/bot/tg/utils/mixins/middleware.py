from functools import wraps
from logging import Logger, getLogger
from typing import Callable

from aiogram.dispatcher.middlewares.data import MiddlewareData
from aiogram.types import CallbackQuery, Message, User

from bot.tg.text.builder import TextBuilder


class LoggerMiddlewareMixin:
    """
    Mixin providing logging functionality for middleware components.

    Creates a dedicated logger instance for middleware components, allowing
    for consistent logging across different router types.
    """

    def __init__(self, router_name: str = "middleware") -> None:
        self.router_name = router_name
        self.logger = getLogger(self.router_name)


class GetMessageMixin:
    """Mixin for extracting Message objects from Telegram events."""

    def get_message(self, event: Message | CallbackQuery) -> Message:
        if isinstance(event, Message):
            return event
        if isinstance(event, CallbackQuery):
            return event.message


class GetUserMixin:
    """Mixin for extracting User objects from Telegram events."""

    def get_user(self, data: MiddlewareData) -> User:
        return data.get("event_from_user", None)


class GetMessageBuilderMixin:
    """Mixin for extracting a TextBuilder instance from context data."""

    def __init__(self, *args, **kwargs) -> None:
        if not isinstance(self, LoggerMiddlewareMixin):
            raise TypeError(
                "GetMessageBuilderMixin must be used with LoggerMiddlewareMixin"
            )
        self.logger: Logger
        super().__init__(*args, **kwargs)

    def get_text_builder(self, data: dict) -> TextBuilder:
        text_builder = data.get("text_builder", None)
        if not isinstance(text_builder, TextBuilder):
            self.logger.warning(
                "passed data not contains text_builder, fallback to "
                "default. Use MessageBuilderMiddleware.decorator to define "
                f"lang. {data=}"
            )
            text_builder = TextBuilder()
        return text_builder


class HandlerMixin:
    """Mixin for creating decorator-based middleware handlers."""

    def decorator(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(event: Message | CallbackQuery, **kwargs):
            # Mimic middleware behavior through kwargs
            return await self.__call__(lambda e, d: func(e, **d), event, kwargs)

        return wrapper
