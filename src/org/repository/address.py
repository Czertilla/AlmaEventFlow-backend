from core.repository.address import AddressBaseRepo

from org.models.address import AddressORM as Model


class AddressRepo(AddressBaseRepo[Model]):
    model = Model
