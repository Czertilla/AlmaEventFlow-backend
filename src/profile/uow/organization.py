from profile.repository.organization import OrganizationRepo

from core.uow.event.organization import OrganizationAUOW
from core.uow.sqlalchemy import UnitOfWork


class OrganizationMixin:
    organizations: OrganizationRepo


class OrganizationUOW(UnitOfWork, OrganizationMixin, OrganizationAUOW): ...
