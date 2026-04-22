from core.uow.sqlalchemy import UnitOfWork
from event.repository.attendance import AttendanceRepo


class AttendanceMixin:
    attendances: AttendanceRepo


class AttendanceUOW(UnitOfWork, AttendanceMixin): ...