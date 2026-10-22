from core.uow.sqlalchemy import UnitOfWork
from org.repository.faculty import FacultyRepo
from org.repository.university import UniversityRepo


class UniversityMixin:
    universities: UniversityRepo


class UniversityUOW(UnitOfWork, UniversityMixin):
    faculties: FacultyRepo