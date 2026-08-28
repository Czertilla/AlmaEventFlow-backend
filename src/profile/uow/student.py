from profile.repository.student import (
    StudentDegreeRepo,
    StudentGroupRepo,
    StudentRepo,
)

from core.uow.sqlalchemy import UnitOfWork


class StudentMixin:
    students: StudentRepo
    student_groups: StudentGroupRepo
    student_degrees: StudentDegreeRepo


class StudentUOW(UnitOfWork, StudentMixin): ...

