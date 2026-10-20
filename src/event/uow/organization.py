from core.uow.event.organization import OrganizationAUOW
from core.uow.sqlalchemy import UnitOfWork
from event.repository.organization import OrganizationRepo
from event.uow.collective import CollectiveMixin


class OrganizationMixin:
    organizations: OrganizationRepo


class OrganizationUOW(  # pyright: ignore[reportIncompatibleVariableOverride]
    UnitOfWork, OrganizationMixin, CollectiveMixin, OrganizationAUOW
): ...
