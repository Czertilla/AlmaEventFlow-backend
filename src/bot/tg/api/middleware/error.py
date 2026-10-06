from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from inspect import Traceback
from typing import Any, Self
from uuid import UUID, uuid4

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from fastapi import HTTPException

from bot.enum.emoji import Emoji
from bot.enum.locales import LocaleKey
from bot.tg.text.builder import TextBuilder
from bot.tg.utils.mixins.middleware import GetUserMixin, LoggerMiddlewareMixin

ErrorEvent = Message | CallbackQuery | Any
HandlerCallable = Callable[[ErrorEvent, dict[str, Any]], Awaitable[Any]]
ExceptionHandler = Callable[
    [type[BaseException], Any, Traceback, ErrorEvent, dict[str, Any]],
    Awaitable[Any],
]


class ErrorHandlerMiddleware(
    BaseMiddleware, LoggerMiddlewareMixin, GetUserMixin
):
    def __init__(
        self,
        router_name: str = "error_handler_middleware",
        *,
        notify_user: bool = True,
        exception_handlers: Iterable[
            tuple[type[BaseException], ExceptionHandler]
        ]
        | None = None,
    ) -> None:
        super().__init__(router_name)
        self.notify_user = notify_user
        self._exception_handlers: list[
            tuple[type[BaseException], ExceptionHandler]
        ] = []
        if exception_handlers:
            for exc_type, handler in exception_handlers:
                self.register_exception_handler(exc_type, handler)
        self.register_exception_handler(
            HTTPException, self._handle_http_exception
        )
        self.register_exception_handler(
            TelegramBadRequest, self._handle_bad_request
        )

    async def __call__(
        self,
        handler: HandlerCallable,
        event: ErrorEvent,
        data: dict[str, Any],
    ) -> object:
        async with self.Guard(self, event, data):
            return await handler(event, data)

    def register_exception_handler(
        self,
        exception_type: type[BaseException],
        handler: ExceptionHandler,
    ) -> None:
        self._exception_handlers.append((exception_type, handler))

    class Guard:
        def __init__(
            self,
            middleware: ErrorHandlerMiddleware,
            event: ErrorEvent,
            data: dict[str, Any],
        ) -> None:
            self.middleware = middleware
            self.event = event
            self.data = data

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            if exc:
                await self.middleware._handle_exception(
                    exc_type, exc, tb, self.event, self.data
                )
                return True
            return False

    async def _handle_exception(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        tb: Traceback,
        event: ErrorEvent,
        data: dict[str, Any],
    ) -> None:
        self._ensure_error_id(exc)
        handler = self._resolve_handler(exc)
        if handler:
            await handler(exc_type, exc, tb, event, data)
            return
        await self._handle_unexpected_error(exc_type, exc, tb, event, data)
        await self._notify_user(exc, event, data)

    def _ensure_error_id(self, err: BaseException) -> UUID:
        err_id = getattr(err, "id", None)
        if err_id is None:
            err_id = uuid4()
            setattr(err, "id", err_id)  # noqa: B010
        return err_id

    def _resolve_handler(self, err: BaseException) -> ExceptionHandler | None:
        for exc_type, handler in self._exception_handlers:
            if isinstance(err, exc_type):
                return handler
        return None

    async def _handle_http_exception(
        self,
        exc_type: type[BaseException],
        exc: HTTPException,
        tb: Traceback,
        event: ErrorEvent,
        data: dict[str, Any],
    ) -> None:
        err_id = getattr(exc, "id", None)
        self.logger.error(
            f"HTTPException during handling {event=}: {exc.detail}",
            exc_info=(exc_type, exc, tb),
            stack_info=True,
            extra={"err_id": str(err_id)},
        )

    async def _handle_bad_request(
        self,
        exc_type: type[BaseException],
        exc: TelegramBadRequest,
        tb: Traceback,
        event: ErrorEvent,
        data: dict[str, Any],
    ) -> None:
        if "message is not modified" in str(exc).lower():
            self.logger.debug("edit skipped, nothing changed: %s", exc)
            return
        await self._handle_unexpected_error(exc_type, exc, tb, event, data)
        await self._notify_user(exc, event, data)

    async def _handle_unexpected_error(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        tb: Traceback,
        event: ErrorEvent,
        data: dict[str, Any],
    ) -> None:
        err_id = getattr(exc, "id", None)
        self.logger.critical(
            f"Unexpected error {exc!s} during ",
            exc_info=(exc_type, exc, tb),
            stack_info=True,
            extra={"err_id": str(err_id)},
        )

    async def _notify_user(
        self, err: BaseException, event: ErrorEvent, data: dict[str, Any]
    ) -> None:
        if not self.notify_user:
            return
        update_event = getattr(event, "event", None)
        user = data.get("user")
        text_builder = TextBuilder(getattr(user, "language_code", None))
        message = await self.format_user_message(err, text_builder)
        try:
            if isinstance(update_event, CallbackQuery):
                target = update_event.message
                if isinstance(target, Message):
                    await target.answer(message)
            elif isinstance(update_event, Message):
                await update_event.answer(message)
        except Exception as exc:
            self.logger.critical(
                f"Failed to notify user about error {getattr(err, 'id', None)}",
                stack_info=True,
                exc_info=exc,
            )

    async def format_user_message(
        self, err: BaseException, text_builder: TextBuilder
    ) -> str:
        err_id = getattr(err, "id", None)
        phrase = await text_builder.get_phrase(
            LocaleKey.Error.unexpected, ch=Emoji.warning
        )
        return f"{phrase}\n<code>{err_id}</code>"
