from core.uow.sqlalchemy import UnitOfWork
from profile.repository.student import (
    StudentRepo,
    StudentGroupRepo,
    StudentDegreeRepo,
)


class StudentMixin:
    students: StudentRepo
    student_groups: StudentGroupRepo
    student_degrees: StudentDegreeRepo


class StudentUOW(UnitOfWork, StudentMixin): ...

