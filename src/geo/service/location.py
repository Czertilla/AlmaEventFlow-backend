from logging import getLogger
from typing import Any
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import selectinload

from core.dto.base import dto_dict
from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.schema.message.geo import LocationData
from core.service.base import BaseService, required_transaction
from geo.api.kafka.pub.location import (
    on_location_created,
    on_location_deleted,
    on_location_updated,
)
from geo.dto.location import (
    LocationCreateDTO,
    LocationDTO,
    LocationFilterDTO,
    LocationPatchDTO,
    LocationPutDTO,
)
from geo.dto.point import PointDTO
from geo.exc.address import AddressNotExistsException
from geo.exc.location import LocationNotExistsException
from geo.filter.location import LocationFilter
from geo.models.address import AddressORM
from geo.models.location import LocationORM
from geo.models.spot import point_from_geometry
from geo.service.mapping import address_to_dto
from geo.uow.location import LocationUOW

logger = getLogger()

_WITH_ADDRESS = (selectinload(LocationORM.address),)
"""So ``map_uri`` can fall back to the linked address's own ``spot`` for an
address-anchored location (which has no ``spot`` of its own) -- read paths
only, RETURNING-based mutation results don't support eager-loading a
relationship in the same statement."""


def _display_name(location: LocationDTO) -> str | None:
    return location.name or (location.address.name if location.address else None)


class LocationService(BaseService[LocationUOW]):
    @staticmethod
    def _to_dto(location: LocationORM) -> LocationDTO:
        address = location.address
        return LocationDTO(
            id=location.id,
            name=location.name,
            address_id=location.address_id,
            spot=point_from_geometry(location.spot),
            address=address_to_dto(address) if address else None,
            created_at=location.created_at,
            edited_at=location.edited_at,
        )

    @required_transaction
    async def _create(self, location_create: LocationCreateDTO) -> LocationORM:
        return await self.uow.locations.add_n_return(dto_dict(location_create))

    @required_transaction
    async def _read(self, location_id: UUID) -> LocationORM:
        location = await self.uow.locations.get_by_id(
            location_id, options=_WITH_ADDRESS
        )
        if location is None:
            raise LocationNotExistsException()
        return location

    @required_transaction
    async def _find_address_proxy(self, address_id: UUID) -> LocationORM:
        stmt = (
            select(LocationORM)
            .where(
                LocationORM.address_id == address_id,
                LocationORM.name.is_(None),
            )
            .options(*_WITH_ADDRESS)
        )
        return (await self.uow.session.execute(stmt)).unique().scalar_one()

    @required_transaction
    async def _ensure_address_proxy(self, address_id: UUID) -> tuple[LocationORM, bool]:
        address_exists = await self.uow.session.scalar(
            select(exists().where(AddressORM.id == address_id))
        )
        if not address_exists:
            raise AddressNotExistsException()
        created = await self.uow.locations.insert_address_proxy(address_id) is not None
        proxy = await self._find_address_proxy(address_id)
        return proxy, created

    @required_transaction
    async def _update(
        self,
        location_id: UUID,
        location_data: dict[str, Any],
        *,
        flush: bool = False,
    ) -> LocationORM:
        location = await self.uow.locations.update_one(
            location_id, location_data, flush
        )
        if location is None:
            raise LocationNotExistsException()
        return location

    @required_transaction
    async def _upsert(self, location_put: LocationPutDTO) -> LocationORM:
        location = await self.uow.locations.upsert(dto_dict(location_put))
        if location is None:
            raise LocationNotExistsException()
        return location

    @required_transaction
    async def _delete(self, location_id: UUID) -> None:
        await self.uow.locations.delete_one(location_id)

    async def create(self, location_create: LocationCreateDTO) -> LocationDTO:
        if location_create.address_id and location_create.name is None:
            return await self.find_or_create_address_proxy(location_create.address_id)
        async with self.uow as uow:
            created = await self._create(location_create)
            result = self._to_dto(await self._read(created.id))
            await uow.commit()
        await on_location_created(
            [LocationData(id=result.id, name=_display_name(result))]
        )
        return result

    async def read(self, location_id: UUID) -> LocationDTO:
        async with self.uow:
            return self._to_dto(await self._read(location_id))

    async def patch(self, location_patch: LocationPatchDTO) -> LocationDTO:
        async with self.uow as uow:
            location_data = dto_dict(location_patch, only_set=True, exclude={"id"})
            updated = await self._update(location_patch.id, location_data)
            result = self._to_dto(await self._read(updated.id))
            await uow.commit()
        await on_location_updated(
            [LocationData(id=result.id, name=_display_name(result))]
        )
        return result

    async def put(self, location_put: LocationPutDTO) -> LocationDTO:
        async with self.uow as uow:
            upserted = await self._upsert(location_put)
            result = self._to_dto(await self._read(upserted.id))
            await uow.commit()
        await on_location_updated(
            [LocationData(id=result.id, name=_display_name(result))]
        )
        return result

    async def delete(self, location_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(location_id)
            await uow.commit()
        await on_location_deleted([location_id])

    async def search(
        self,
        filter: LocationFilterDTO,
        page_params: PageParamDTO = PageParamDTO(),
        near: PointDTO | None = None,
    ) -> PageDTO[LocationDTO]:
        async with self.uow as uow:
            items, total = await uow.locations.search(
                LocationFilter.from_dto(filter),
                page_params,
                options=_WITH_ADDRESS,
                near=near,
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def search_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        page_params: PageParamDTO = PageParamDTO(),
    ) -> PageDTO[LocationDTO]:
        async with self.uow as uow:
            items, total = await uow.locations.search_in_bbox(
                min_lat, min_lon, max_lat, max_lon, page_params
            )
            return PageDTO(
                items=[self._to_dto(item) for item in items],
                pagination=PaginationDTO(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def find_or_create_address_proxy(self, address_id: UUID) -> LocationDTO:
        """The "just this address, nothing more specific" case: a
        location with no name of its own, anchored purely to the address.
        Idempotent and race-safe -- concurrent calls for the same address
        resolve to one row (unique partial index + ON CONFLICT DO NOTHING)."""
        async with self.uow as uow:
            proxy, created = await self._ensure_address_proxy(address_id)
            result = self._to_dto(proxy)
            await uow.commit()
        if created:
            await on_location_created(
                [LocationData(id=result.id, name=_display_name(result))]
            )
        return result

    async def create_from_address(
        self, address_id: UUID, name: str | None
    ) -> LocationDTO:
        if name is None:
            return await self.find_or_create_address_proxy(address_id)
        return await self.create(
            LocationCreateDTO(name=name, address_id=address_id, spot=None)
        )
