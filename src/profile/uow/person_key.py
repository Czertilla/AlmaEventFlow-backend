from profile.repository.person_key import PersonKeyRepo

from core.uow.sqlalchemy import UnitOfWork


class PersonKeyMixin:
    person_keys: PersonKeyRepo


class PersonalDataUOW(UnitOfWork, PersonKeyMixin): ...
