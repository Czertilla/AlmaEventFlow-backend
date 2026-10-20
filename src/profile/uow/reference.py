from profile.uow.diet import DietMixin
from profile.uow.organization import OrganizationMixin
from profile.uow.student import StudentMixin

from core.uow.sqlalchemy import UnitOfWork


class ReferenceUOW(UnitOfWork, DietMixin, StudentMixin, OrganizationMixin): ...
