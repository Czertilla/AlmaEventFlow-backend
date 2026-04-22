from core.uow.sqlalchemy import UnitOfWork
from org.repository.organization import OrganizationRepo
from org.uow.collective import CollectiveMixin


class OrganizationMixin:
    organizations: OrganizationRepo


class OrganizationUOW(UnitOfWork, OrganizationMixin, CollectiveMixin): ...
