from core.uow.sqlalchemy import UnitOfWork
from geo.repository.address import AddressAlchemyRepo


class AddressORMMixin:
    addresses: AddressAlchemyRepo


class AddressUOW(UnitOfWork, AddressORMMixin): ...
