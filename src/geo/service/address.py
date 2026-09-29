from logging import getLogger
from uuid import UUID

from core.schema.message.geo import AddressData
from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction
from geo.api.kafka.pub.location import on_location_deleted
from geo.api.kafka.pub.address import (
    on_address_created,
    on_address_deleted,
    on_address_updated,
)
from geo.exc.address import AddressNotExistsException
from geo.filter.address import AddressFilter
from geo.models.address import AddressORM
from geo.schema.address import (
    AddressCreate,
    AddressPatch,
    AddressPut,
    AddressRead,
)
from geo.schema.point import Point
from geo.uow.address import AddressUOW

logger = getLogger(__name__)


class AddressService(BaseService[AddressUOW]):
    @required_transaction
    async def _create(self, address_create: AddressCreate) -> AddressORM:
        return await self.uow.addresses.add_n_return(
            address_create.model_dump()
        )

    @required_transaction
    async def _read(self, address_id: UUID) -> AddressORM | None:
        address = await self.uow.addresses.get_by_id(address_id)
        if address is None:
            raise AddressNotExistsException()
        return address

    @required_transaction
    async def _update(
        self, address_id: UUID, address_data: dict, *, flush: bool = False
    ) -> AddressORM:
        address = await self.uow.addresses.update_one(
            address_id, address_data, flush
        )
        if address is None:
            raise AddressNotExistsException()
        return address

    @required_transaction
    async def _upsert(self, address_put: AddressPut) -> AddressORM:
        return await self.uow.addresses.upsert(address_put.model_dump())

    @required_transaction
    async def _delete(self, address_id: UUID) -> list[UUID]:
        location_ids = await self.uow.locations.delete_by_address(address_id)
        await self.uow.addresses.delete_one(address_id)
        return location_ids

    async def create(self, address_create: AddressCreate) -> AddressRead:
        async with self.uow as uow:
            result = AddressRead.model_validate(
                await self._create(address_create)
            )
            await uow.commit()
        await on_address_created([AddressData(id=result.id, name=result.name)])
        return result

    async def read(self, address_id: UUID) -> AddressRead:
        async with self.uow:
            return AddressRead.model_validate(await self._read(address_id))

    async def patch(self, address_patch: AddressPatch) -> AddressRead:
        async with self.uow as uow:
            address_data = address_patch.model_dump()
            for required in ("name", "city_id"):
                if address_data.get(required) is None:
                    address_data.pop(required, None)
            if address_patch.parsed and "name" not in address_data:
                composed = address_patch.parsed.compose_name()
                if composed:
                    address_data["name"] = composed
            result = AddressRead.model_validate(
                await self._update(address_data.pop("id"), address_data)
            )
            await uow.commit()
        await on_address_updated([AddressData(id=result.id, name=result.name)])
        return result

    async def put(self, address_put: AddressPut) -> AddressRead:
        async with self.uow as uow:
            result = AddressRead.model_validate(
                await self._upsert(address_put)
            )
            await uow.commit()
        await on_address_updated([AddressData(id=result.id, name=result.name)])
        return (
            result.model_dump() | address_put.model_dump()
        )  # TODO remove bypass

    async def delete(self, address_id: UUID) -> None:
        async with self.uow as uow:
            location_ids = await self._delete(address_id)
            await uow.commit()
        if location_ids:
            await on_location_deleted(location_ids)
        await on_address_deleted([address_id])

    async def search(
        self,
        filter: AddressFilter,
        page_params: SPageParam = SPageParam(),
        near: Point | None = None,
    ) -> SPage[AddressRead]:
        async with self.uow as uow:
            items, total = await uow.addresses.search(filter, page_params, near=near)
            return SPage(
                items=[AddressRead.model_validate(item) for item in items],
                pagination=SPagination(page=page_params.page, limit=page_params.limit, total=total),
            )

    async def search_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        page_params: SPageParam = SPageParam(),
    ) -> SPage[AddressRead]:
        async with self.uow as uow:
            items, total = await uow.addresses.search_in_bbox(
                min_lat, min_lon, max_lat, max_lon, page_params
            )
            return SPage(
                items=[AddressRead.model_validate(item) for item in items],
                pagination=SPagination(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
