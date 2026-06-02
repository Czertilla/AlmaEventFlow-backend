from logging import getLogger

from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction

from geo.exc.address import AddressNotExistsException
from geo.filter.address import AddressFilter
from geo.models.address import AddressORM
from geo.schema.address import (
    AddressCreate,
    AddressPatch,
    AddressPut,
    AddressRead,
)
from geo.uow.address import AddressUOW

logger = getLogger(__name__)


class AddressService(BaseService[AddressUOW]):
    @required_transaction
    async def _create(self, address_create: AddressCreate) -> AddressORM:
        return await self.uow.addresses.add_n_return(
            address_create.model_dump()
        )

    @required_transaction
    async def _read(self, address_id: int) -> AddressORM | None:
        address = await self.uow.addresses.get_by_id(address_id)
        if address is None:
            raise AddressNotExistsException()
        return address

    @required_transaction
    async def _update(
        self, address_id: int, address_data: dict, *, flush: bool = False
    ) -> AddressORM:
        address = await self.uow.addresses.update_one(
            address_id, address_data, flush
        )
        if address is None:
            raise AddressNotExistsException()
        return address

    async def create(self, address_create: AddressCreate) -> AddressRead:
        async with self.uow as uow:
            result = AddressRead.model_validate(
                await self._create(address_create)
            )
            await uow.commit()
        return result

    async def read(self, address_id: int) -> AddressRead:
        async with self.uow:
            return AddressRead.model_validate(await self._read(address_id))

    async def patch(self, address_patch: AddressPatch) -> AddressRead:
        async with self.uow as uow:
            address_data = address_patch.model_dump()
            result = AddressRead.model_validate(
                await self._update(address_data.pop("id"), address_data)
            )
            await uow.commit()
        return result

    async def put(self, address_put: AddressPut) -> AddressRead:
        async with self.uow as uow:
            result = AddressRead.model_validate(
                await self.uow.addresses.upsert(address_put.model_dump())
            )
            await uow.commit()
        return (
            result.model_dump() | address_put.model_dump()
        )  # TODO remove bypass

    async def delete(self, address_id: int) -> None:
        async with self.uow as uow:
            await self.uow.addresses.delete_one(address_id)
            await uow.commit()

    async def search(self, filter: AddressFilter, page_params: SPageParam = SPageParam()) -> SPage[AddressRead]:
        async with self.uow as uow:
            items, total = await uow.addresses.search(filter, page_params)
            return SPage(
                items=[AddressRead.model_validate(item) for item in items],
                pagination=SPagination(page=page_params.page, limit=page_params.limit, total=total),
            )
