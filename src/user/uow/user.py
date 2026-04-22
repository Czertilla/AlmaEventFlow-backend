from core.uow.sqlalchemy import UnitOfWork

from user.repositories.user import UserRepo


class UserMixin:
    users: UserRepo


class UserUOW(UnitOfWork, UserMixin): ...
