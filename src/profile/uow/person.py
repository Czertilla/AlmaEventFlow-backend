from core.uow.sqlalchemy import UnitOfWork
from profile.repository.person import PersonRepo
from profile.uow.contact import ContactMixin


class PersonMixin:
    persons: PersonRepo


class PersonUOW(UnitOfWork, PersonMixin, ContactMixin): ...

class PersonContactUOW(UnitOfWork, PersonMixin, ContactMixin): ...