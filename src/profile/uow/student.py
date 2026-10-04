from profile.repository.student import (
    StudentDegreeRepo,
    StudentGroupRepo,
    StudentRepo,
)
from profile.uow.profile import ProfileMixin

from core.uow.sqlalchemy import UnitOfWork


class StudentMixin:
    students: StudentRepo
    student_groups: StudentGroupRepo
    student_degrees: StudentDegreeRepo


class StudentUOW(UnitOfWork, StudentMixin, ProfileMixin): ...
