from core.uow.sqlalchemy import UnitOfWork
from org.repository.collective import CollectiveRepo
from org.uow.university import UniversityMixin


class CollectiveMixin:
    collectives: CollectiveRepo


class CollectiveUOW(UnitOfWork, CollectiveMixin, UniversityMixin): ...
