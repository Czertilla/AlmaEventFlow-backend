from core.uow.sqlalchemy import UnitOfWork
from org.repository.faculty import FacultyRepo
from org.uow.university import UniversityMixin


class FacultyMixin:
    faculties: FacultyRepo


class FacultyUOW(UnitOfWork, FacultyMixin, UniversityMixin): ...