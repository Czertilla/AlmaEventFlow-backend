from core.uow.sqlalchemy import UnitOfWork
from event.uow.attendance import AttendanceMixin
from event.uow.collective import CollectiveMixin
from event.uow.event import EventMixin
from event.uow.member import MemberMixin
from event.uow.participation import ParticipationMixin
from event.uow.stage import StageMixin


class EventComposeUOW(UnitOfWork, CollectiveMixin, EventMixin, StageMixin, ParticipationMixin, MemberMixin, AttendanceMixin):
    ...


class ParticipationComposeUOW(UnitOfWork, ParticipationMixin, MemberMixin, AttendanceMixin):
    ...
