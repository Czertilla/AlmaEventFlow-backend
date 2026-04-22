from core.uow.sqlalchemy import UnitOfWork
from event.repository.role import RoleRepo


class RoleMixin:
    roles: RoleRepo


class RoleUOW(UnitOfWork, RoleMixin): ...