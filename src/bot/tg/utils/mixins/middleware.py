from collections.abc import Awaitable, Callable
from functools import wraps
from logging import Logger, getLogger
from typing import Any, Protocol

from aiogram.dispatcher.middlewares.data import MiddlewareData
from aiogram.types import (
    CallbackQuery,
    MaybeInaccessibleMessageUnion,
    Message,
    User,
)

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

    def get_message(
        self, event: Message | CallbackQuery
    ) -> MaybeInaccessibleMessageUnion | None:
        if isinstance(event, Message):
            return event
        return event.message


class GetUserMixin:
    """Mixin for extracting User objects from Telegram events."""

    def get_user(self, data: MiddlewareData) -> User | None:
        return data.get("event_from_user", None)


class GetMessageBuilderMixin:
    """Mixin for extracting a TextBuilder instance from context data."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if not isinstance(self, LoggerMiddlewareMixin):
            raise TypeError(
                "GetMessageBuilderMixin must be used with LoggerMiddlewareMixin"
            )
        self.logger: Logger
        super().__init__(*args, **kwargs)

    def get_text_builder(self, data: dict[str, Any]) -> TextBuilder:
        text_builder = data.get("text_builder")
        if not isinstance(text_builder, TextBuilder):
            self.logger.warning(
                "passed data not contains text_builder, fallback to "
                "default. Use MessageBuilderMiddleware.decorator to define "
                f"lang. {data=}"
            )
            text_builder = TextBuilder()
        return text_builder


class _CallableMiddleware(Protocol):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any: ...


class HandlerMixin:
    """Mixin for creating decorator-based middleware handlers."""

    def decorator(
        self: _CallableMiddleware, func: Callable[..., Awaitable[Any]]
    ) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(
            event: Message | CallbackQuery, **kwargs: Any
        ) -> Any:
            return await self.__call__(lambda e, d: func(e, **d), event, kwargs)

        return wrapper
