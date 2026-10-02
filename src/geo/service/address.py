from logging import getLogger
from uuid import UUID

from core.schema.message.geo import AddressData
from core.schema.v1.pagination import PageParamV1, PageV1, PaginationV1
from core.service.base import BaseService, required_transaction
from geo.api.kafka.pub.address import (
    on_address_created,
    on_address_deleted,
    on_address_updated,
)
from geo.api.kafka.pub.location import on_location_deleted
from geo.exc.address import AddressNotExistsException
from geo.filter.address import AddressFilter
from geo.models.address import AddressORM
from geo.schema.address import (
    AddressCascadeCreate,
    AddressCreate,
    AddressFields,
    AddressPatch,
    AddressPut,
    AddressRead,
)
from geo.schema.point import Point
from geo.service.geography import resolve_or_create_city
from geo.service.live_fetch import schedule_live_fetch
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

    async def create_cascade(self, data: AddressCascadeCreate) -> AddressRead:
        """Like ``create``, but for a hand-entered address whose city may
        not exist yet: resolves/creates the country/region/city by name
        (see ``geo.service.geography``) in the same transaction as the
        address itself, instead of requiring a pre-existing ``city_id``."""
        async with self.uow as uow:
            city_id = await resolve_or_create_city(
                uow, data.city.country, data.city.region, data.city.name
            )
            fields = AddressFields(
                house=data.house,
                district=data.district,
                street=data.street,
                building=data.building,
                apartment=data.apartment,
            )
            address_create = AddressCreate(
                city_id=city_id, spot=data.spot, parsed=fields
            )
            result = AddressRead.model_validate(await self._create(address_create))
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
        page_params: PageParamV1 = PageParamV1(),
        near: Point | None = None,
    ) -> PageV1[AddressRead]:
        async with self.uow as uow:
            items, total = await uow.addresses.search(filter, page_params, near=near)
            page = PageV1(
                items=[AddressRead.model_validate(item) for item in items],
                pagination=PaginationV1(page=page_params.page, limit=page_params.limit, total=total),
            )
        if near is not None:
            schedule_live_fetch(near, sessionmaker=self.uow.session_factory)
        return page

    async def search_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        page_params: PageParamV1 = PageParamV1(),
    ) -> PageV1[AddressRead]:
        async with self.uow as uow:
            items, total = await uow.addresses.search_in_bbox(
                min_lat, min_lon, max_lat, max_lon, page_params
            )
            return PageV1(
                items=[AddressRead.model_validate(item) for item in items],
                pagination=PaginationV1(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
