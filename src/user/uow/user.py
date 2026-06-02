from core.uow.sqlalchemy import UnitOfWork
from user.repositories.user import UserRepo
from user.repository.person import PersonRepo
from user.repository.session import SessionRepo


class UserMixin:
    users: UserRepo

class PersonMixin:
    persons: PersonRepo

class SessionMixin:
    sessions: SessionRepo


class UserUOW(UnitOfWork, UserMixin, PersonMixin, SessionMixin): ...
