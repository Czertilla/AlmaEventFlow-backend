from core.uow.event.organization import OrganizationAUOW
from core.uow.sqlalchemy import UnitOfWork
from profile.repository.organization import OrganizationRepo


class OrganizationMixin:
    organizations: OrganizationRepo


class OrganizationUOW(UnitOfWork, OrganizationMixin, OrganizationAUOW): ...
