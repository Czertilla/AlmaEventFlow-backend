from logging import getLogger

from aiogram import Dispatcher, F, Router

from bot.tg.api.middleware.error import ErrorHandlerMiddleware
from bot.tg.api.middleware.logging import UpdateLoggingMiddleware
from bot.tg.api.middleware.user import UserUpdateMiddleware
from bot.tg.api.middleware.username import UsernameWarningMiddleware
from core.utils.imports import load_common

routers: list[Router] = sorted(
    load_common(__name__, "router", Router), key=lambda x: x.name
)

logger = getLogger(__name__)


def register_routers(dp: Dispatcher) -> None:
    dp.include_routers(*routers)

    dp.update.middleware(ErrorHandlerMiddleware())
    dp.update.middleware(UpdateLoggingMiddleware())
    dp.update.middleware(UserUpdateMiddleware())
    dp.update.middleware(UsernameWarningMiddleware())
    # No blanket private-only filter here: /setup_chat only works in groups,
    # and the attendance callback works in both — each router restricts its
    # own chat-type scope instead (see command/main.py, callback/menu.py,
    # command/setup_chat.py, etc.).
    dp.inline_query.filter(F.chat_type.in_(["private", "sender"]))
