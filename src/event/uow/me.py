from core.uow.sqlalchemy import UnitOfWork
from event.uow.collective import CollectiveMixin
from event.uow.event import EventMixin
from event.uow.stage import StageMixin
from event.uow.participation import ParticipationMixin
from event.uow.member import MemberMixin
from event.uow.attendance import AttendanceMixin


class EventComposeUOW(UnitOfWork, CollectiveMixin, EventMixin, StageMixin, ParticipationMixin, MemberMixin, AttendanceMixin):
    pass


class ParticipationComposeUOW(UnitOfWork, ParticipationMixin, MemberMixin, AttendanceMixin):
    pass
