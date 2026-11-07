from profile.repository.person_key import PersonKeyRepo
from profile.repository.registry_rows import RegistryRowsRepo
from profile.uow.access_log import AccessLogMixin
from profile.uow.outbox import OutboxMixin
from profile.uow.person import PersonMixin

from core.uow.sqlalchemy import UnitOfWork


class PersonKeyMixin:
    person_keys: PersonKeyRepo
    registry_rows: RegistryRowsRepo


class PersonalDataUOW(
    UnitOfWork, PersonKeyMixin, AccessLogMixin, OutboxMixin, PersonMixin
): ...
