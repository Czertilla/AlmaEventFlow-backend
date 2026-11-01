from profile.uow.organization import OrganizationMixin
from profile.uow.visibility import VisibilityMixin

from core.uow.sqlalchemy import UnitOfWork


class AccessUOW(UnitOfWork, OrganizationMixin, VisibilityMixin): ...
