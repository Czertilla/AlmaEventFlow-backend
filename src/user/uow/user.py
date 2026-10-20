from core.uow.sqlalchemy import UnitOfWork
from user.repository.person import PersonRepo
from user.repository.refresh_token import RefreshTokenRepo
from user.repository.session import SessionRepo
from user.repository.user import UserRepo


class UserMixin:
    users: UserRepo


class PersonMixin:
    persons: PersonRepo


class SessionMixin:
    sessions: SessionRepo


class RefreshTokenMixin:
    refresh_tokens: RefreshTokenRepo


class UserUOW(UnitOfWork, UserMixin, PersonMixin, SessionMixin, RefreshTokenMixin): ...
