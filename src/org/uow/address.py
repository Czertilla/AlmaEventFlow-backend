from core.uow.event.address import AddressAUOW
from core.uow.sqlalchemy import UnitOfWork

from org.repository.address import AddressRepo


class AddressMixin:
    addresses: AddressRepo


class AddressUOW(UnitOfWork, AddressMixin, AddressAUOW): ...
