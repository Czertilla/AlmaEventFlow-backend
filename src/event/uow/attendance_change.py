from core.uow.sqlalchemy import UnitOfWork
from event.uow.attendance import AttendanceMixin
from event.uow.view import ViewMixin


class AttendanceChangeUOW(UnitOfWork, AttendanceMixin, ViewMixin): ...
