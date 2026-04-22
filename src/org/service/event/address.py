from typing import Generic, TypeVar
from uuid import UUID
from core.service.base import BaseService, required_transaction
from core.uow.event.address import AddressAUOW
from core.schema.message.geo import AddressData, AddressDelete

UOW = TypeVar("UOW", bound=AddressAUOW)


class AddressEventService(BaseService[UOW], Generic[UOW]):
    @required_transaction
    async def _create(self, address: AddressData):
        await self.uow.addresses.add_n_return(data=address.model_dump())

    @required_transaction
    async def _upsert(self, address: AddressData):
        await self.uow.addresses.upsert(data=address.model_dump())

    @required_transaction
    async def _delete(self, address_id: UUID):
        await self.uow.addresses.delete_one(address_id)

    async def create(self, address: AddressData) -> None:
        async with self.uow as uow:
            await self._create(address)
            await uow.commit()

    async def update(self, address: AddressData) -> None:
        async with self.uow as uow:
            await self._upsert(address)
            await uow.commit()

    async def delete(self, address: AddressDelete) -> None:
        async with self.uow as uow:
            await self._delete(address.id)
            await uow.commit()
