from core.uow.sqlalchemy import UnitOfWork
from event.repository.member import MemberRepo
from event.uow.role import RoleMixin


class MemberMixin:
    members: MemberRepo


class MemberUOW(UnitOfWork, MemberMixin, RoleMixin): ...