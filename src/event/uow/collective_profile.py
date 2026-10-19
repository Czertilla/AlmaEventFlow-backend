from core.uow.sqlalchemy import UnitOfWork
from event.uow.attendance import AttendanceMixin
from event.uow.collective import CollectiveMixin
from event.uow.member import MemberMixin
from event.uow.person import PersonMixin


class CollectiveProfileUOW(
    UnitOfWork, MemberMixin, AttendanceMixin, CollectiveMixin, PersonMixin
): ...
