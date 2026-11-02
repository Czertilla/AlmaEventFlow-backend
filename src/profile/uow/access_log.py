from profile.repository.access_log import AccessLogRepo
from profile.uow.person import PersonMixin

from core.uow.sqlalchemy import UnitOfWork


class AccessLogMixin:
    access_log: AccessLogRepo


class AccessLogUOW(UnitOfWork, AccessLogMixin, PersonMixin): ...
