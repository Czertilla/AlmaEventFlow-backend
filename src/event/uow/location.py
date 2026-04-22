from core.uow.event.location import LocationAUOW
from core.uow.sqlalchemy import UnitOfWork
from event.repository.location import LocationRepo


class LocationMixin:
    locations: LocationRepo


class LocationUOW(UnitOfWork, LocationMixin, LocationAUOW): ...