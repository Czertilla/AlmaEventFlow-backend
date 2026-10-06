from logging import getLogger

from aiogram import Dispatcher, F, Router
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram.utils.chat_action import ChatActionMiddleware

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
    dp.message.middleware(ChatActionMiddleware())
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    dp.inline_query.filter(F.chat_type.in_(["private", "sender"]))
