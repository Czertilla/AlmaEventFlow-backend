from core.uow.sqlalchemy import UnitOfWork
from event.uow.attendance import AttendanceMixin
from event.uow.collective import CollectiveMixin
from event.uow.member import MemberMixin


class MemberProfileUOW(UnitOfWork, MemberMixin, AttendanceMixin, CollectiveMixin): ...
