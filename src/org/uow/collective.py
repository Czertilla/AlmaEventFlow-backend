from core.uow.sqlalchemy import UnitOfWork
from org.repository.collective import CollectiveRepo


class CollectiveMixin:
    collectives: CollectiveRepo


class CollectiveUOW(UnitOfWork, CollectiveMixin): ...
