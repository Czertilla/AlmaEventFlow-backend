from bot.repository.user import UserRepo
from bot.uow.base import BotUnitOfWork


class UserMixin:
    users: UserRepo


class UserUOW(BotUnitOfWork, UserMixin): ...
