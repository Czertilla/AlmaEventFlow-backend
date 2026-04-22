from core.uow.event.person import PersonAUOW
from core.uow.sqlalchemy import UnitOfWork

from org.repository.person import PersonRepo


class PersonMixin:
    persons: PersonRepo


class PersonUOW(UnitOfWork, PersonMixin, PersonAUOW): ...
