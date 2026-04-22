from core.repository.address import AddressBaseRepo
from core.utils.abstract.unit_of_work import ABCUnitOfWork

class AddressAUOW(ABCUnitOfWork):
    addresses: AddressBaseRepo