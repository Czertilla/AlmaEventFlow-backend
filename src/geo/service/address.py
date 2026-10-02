from dataclasses import replace
from logging import getLogger
from typing import Any
from uuid import UUID

from core.dto.base import dto_dict
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.schema.message.geo import AddressData
from core.service.base import BaseService, required_transaction
from geo.api.kafka.pub.address import (
    on_address_created,
    on_address_deleted,
    on_address_updated,
)
from geo.api.kafka.pub.location import on_location_deleted
from geo.dto.address import (
    AddressCascadeCreateDTO,
    AddressCreateDTO,
    AddressDTO,
    AddressFieldsDTO,
    AddressFilterDTO,
    AddressPatchDTO,
    AddressPutDTO,
)
from geo.dto.point import PointDTO
from geo.exc.address import AddressNotExistsException
from geo.filter.address import AddressFilter
from geo.models.address import AddressORM
from geo.service.geography import resolve_or_create_city
from geo.service.live_fetch import schedule_live_fetch
from geo.service.mapping import address_to_dto
from geo.uow.address import AddressUOW

logger = getLogger(__name__)


class AddressService(BaseService[AddressUOW]):
    @staticmethod
    def _to_dto(address: AddressORM) -> AddressDTO:
        return address_to_dto(address)

    @staticmethod
    def _named(address_create: AddressCreateDTO) -> AddressCreateDTO:
        if address_create.name and address_create.name.strip():
            return address_create
        parsed = address_create.parsed
        name = parsed.compose_name() if parsed else ""
        if not name.strip():
            raise ValueError("either name or parsed address fields are required")
        return replace(address_create, name=name)

    @required_transaction
    async def _create(self, address_create: AddressCreateDTO) -> AddressORM:
        return await self.uow.addresses.add_n_return(
            dto_dict(self._named(address_create))
        )

    @required_transaction
    async def _read(self, address_id: UUID) -> AddressORM:
        address = await self.uow.addresses.get_by_id(address_id)
        if address is None:
            raise AddressNotExistsException()
        return address

    @required_transaction
    async def _update(
        self,
        address_id: UUID,
        address_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> AddressORM:
        address = await self.uow.addresses.update_one(address_id, address_data, flush)
        if address is None:
            raise AddressNotExistsException()
        return address

    @required_transaction
    async def _upsert(self, address_put: AddressPutDTO) -> AddressORM:
        address = await self.uow.addresses.upsert(dto_dict(address_put))
        if address is None:
            raise AddressNotExistsException()
        return address

    @required_transaction
    async def _delete(self, address_id: UUID) -> list[UUID]:
        location_ids = await self.uow.locations.delete_by_address(address_id)
        await self.uow.addresses.delete_one(address_id)
        return location_ids

    async def create(self, address_create: AddressCreateDTO) -> AddressDTO:
        async with self.uow as uow:
            result = self._to_dto(await self._create(address_create))
            await uow.commit()
        await on_address_created([AddressData(id=result.id, name=result.name)])
        return result

    async def create_cascade(self, data: AddressCascadeCreateDTO) -> AddressDTO:
        async with self.uow as uow:
            city_id = await resolve_or_create_city(
                uow, data.city.country, data.city.region, data.city.name
            )
            fields = AddressFieldsDTO(
                house=data.house,
                district=data.district,
                street=data.street,
                building=data.building,
                apartment=data.apartment,
            )
            address_create = AddressCreateDTO(
                city_id=city_id, spot=data.spot, parsed=fields
            )
            result = self._to_dto(await self._create(address_create))
            await uow.commit()
        await on_address_created([AddressData(id=result.id, name=result.name)])
        return result

    async def read(self, address_id: UUID) -> AddressDTO:
        async with self.uow:
            return self._to_dto(await self._read(address_id))

    async def patch(self, address_patch: AddressPatchDTO) -> AddressDTO:
        async with self.uow as uow:
            address_data = dto_dict(address_patch, only_set=True, exclude={"id"})
            for required in ("name", "city_id"):
                if address_data.get(required) is None:
                    address_data.pop(required, None)
            if address_patch.parsed and "name" not in address_data:
                composed = address_patch.parsed.compose_name()
                if composed:
                    address_data["name"] = composed
            result = self._to_dto(await self._update(address_patch.id, address_data))
            await uow.commit()
        await on_address_updated([AddressData(id=result.id, name=result.name)])
        return result

    async def put(self, address_put: AddressPutDTO) -> AddressDTO:
        async with self.uow as uow:
            upserted = await self._upsert(address_put)
            result = self._to_dto(await self._read(upserted.id))
            await uow.commit()
        await on_address_updated([AddressData(id=result.id, name=result.name)])
        return result

    async def delete(self, address_id: UUID) -> None:
        async with self.uow as uow:
            location_ids = await self._delete(address_id)
            await uow.commit()
        if location_ids:
            await on_location_deleted(location_ids)
        await on_address_deleted([address_id])

    async def search(
        self,
        filter: AddressFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
        near: PointDTO | None = None,
    ) -> PageDTO[AddressDTO]:
        async with self.uow as uow:
            items, total = await uow.addresses.search(
                AddressFilter.from_dto(filter), page_params, near=near
            )
            page = PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
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
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[AddressDTO]:
        async with self.uow as uow:
            items, total = await uow.addresses.search_in_bbox(
                min_lat, min_lon, max_lat, max_lon, page_params
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )
