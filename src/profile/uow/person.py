from profile.repository.person import PersonRepo
from profile.uow.contact import ContactMixin

from core.uow.sqlalchemy import UnitOfWork


class PersonMixin:
    persons: PersonRepo


class PersonUOW(UnitOfWork, PersonMixin, ContactMixin): ...

class PersonContactUOW(UnitOfWork, PersonMixin, ContactMixin): ...