from profile.repository.person import PersonRepo
from profile.uow.account import AccountMixin
from profile.uow.contact import ContactMixin
from profile.uow.outbox import OutboxMixin

from core.uow.sqlalchemy import UnitOfWork


class PersonMixin:
    persons: PersonRepo


class PersonUOW(UnitOfWork, PersonMixin, ContactMixin, AccountMixin, OutboxMixin): ...

class PersonContactUOW(UnitOfWork, PersonMixin, ContactMixin): ...