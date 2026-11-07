from core.uow.sqlalchemy import UnitOfWork
from event.uow.collective import CollectiveMixin
from event.uow.member import MemberMixin


class CollectiveAccessUOW(UnitOfWork, CollectiveMixin, MemberMixin): ...
