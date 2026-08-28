from bot.tg.repository.collective_chat import CollectiveChatRepo
from bot.uow.base import BotUnitOfWork


class CollectiveChatMixin:
    collective_chats: CollectiveChatRepo


class CollectiveChatUOW(BotUnitOfWork, CollectiveChatMixin): ...
