from bot.tg.repository.message import TelegramMessageRepo
from bot.uow.base import BotUnitOfWork


class TelegramMessageMixin:
    messages: TelegramMessageRepo


class TelegramMessageUOW(BotUnitOfWork, TelegramMessageMixin): ...
