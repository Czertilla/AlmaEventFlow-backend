from core.uow.sqlalchemy import UnitOfWork
from notify.repository.preference import PreferenceRepo


class PreferenceMixin:
    preferences: PreferenceRepo


class PreferenceUOW(UnitOfWork, PreferenceMixin): ...
