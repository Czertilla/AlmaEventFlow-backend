from core.uow.sqlalchemy import UnitOfWork
from org.uow.faculty import FacultyMixin
from org.uow.organization import OrganizationMixin
from org.uow.university import UniversityMixin


class ReferenceUOW(UnitOfWork, UniversityMixin, FacultyMixin, OrganizationMixin): ...
