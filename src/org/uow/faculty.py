from core.uow.sqlalchemy import UnitOfWork
from org.repository.faculty import FacultyRepo


class FacultyMixin:
    faculties: FacultyRepo


class FacultyUOW(UnitOfWork, FacultyMixin): ...