from core.uow.sqlalchemy import UnitOfWork
from geo.repository.map import MapRepo


class MapMixin:
    map: MapRepo


class MapUOW(UnitOfWork, MapMixin): ...
