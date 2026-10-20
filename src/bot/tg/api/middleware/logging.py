from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any

from aiogram import BaseMiddleware, types

from bot.tg.utils.mixins.middleware import LoggerMiddlewareMixin

logger = getLogger(__name__)


class CommandLoggingMiddleware(BaseMiddleware, LoggerMiddlewareMixin):
    def __init__(self, router_name: str = "commands") -> None:
        super().__init__(router_name)

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if (
            isinstance(event, types.Message)
            and event.text
            and event.text.startswith("/")
        ):
            command = event.text.split()[0]
            self.logger.info(f"handling {command} from {event.chat.id=}")
        else:
            self.logger.warning(
                f"using {self.__class__.__name__} with not commands router "
                f"name={self.logger.name} detected"
            )

        return await handler(event, data)


class UpdateLoggingMiddleware(BaseMiddleware, LoggerMiddlewareMixin):
    def __init__(self, router_name: str = "/") -> None:
        super().__init__(router_name)

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        self.logger.debug(event)
        return await handler(event, data)
