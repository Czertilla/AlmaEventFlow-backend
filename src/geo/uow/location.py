from core.uow.sqlalchemy import UnitOfWork
from geo.repository.location import LocationRepo


class LocationMixin:
    locations: LocationRepo


class LocationUOW(UnitOfWork, LocationMixin): ...
