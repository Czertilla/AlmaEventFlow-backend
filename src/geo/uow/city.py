from core.uow.sqlalchemy import UnitOfWork
from geo.repository.city import CityRepo


class CityMixin:
    cities: CityRepo


class CityUOW(UnitOfWork, CityMixin): ...
