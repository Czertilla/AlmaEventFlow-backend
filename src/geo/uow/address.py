from core.uow.sqlalchemy import UnitOfWork
from geo.repository.address import AddressAlchemyRepo
from geo.repository.coverage import CoverageRepo
from geo.repository.location import LocationRepo


class AddressORMMixin:
    addresses: AddressAlchemyRepo
    locations: LocationRepo
    coverage: CoverageRepo


class AddressUOW(UnitOfWork, AddressORMMixin): ...
