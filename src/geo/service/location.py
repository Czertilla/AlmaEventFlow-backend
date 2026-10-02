from logging import getLogger
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import selectinload

from core.schema.message.geo import LocationData
from core.schema.v1.pagination import PageParamV1, PageV1, PaginationV1
from core.service.base import BaseService, required_transaction
from geo.api.kafka.pub.location import (
    on_location_created,
    on_location_deleted,
    on_location_updated,
)
from geo.exc.address import AddressNotExistsException
from geo.exc.location import LocationNotExistsException
from geo.filter.location import LocationFilter
from geo.models.address import AddressORM
from geo.models.location import LocationORM
from geo.schema.location import (
    LocationCreate,
    LocationPatch,
    LocationPut,
    LocationRead,
)
from geo.schema.point import Point
from geo.uow.location import LocationUOW

logger = getLogger()

_WITH_ADDRESS = (selectinload(LocationORM.address),)
"""So ``LocationRead.map_uri`` can fall back to the linked address's own
``spot`` for an address-anchored location (which has no ``spot`` of its
own) -- read paths only, RETURNING-based mutation results don't support
eager-loading a relationship in the same statement."""


class LocationService(BaseService[LocationUOW]):
    @required_transaction
    async def _create(self, location_create: LocationCreate) -> LocationORM:
        return await self.uow.locations.add_n_return(
            location_create.model_dump()
        )

    @required_transaction
    async def _read(self, location_id: UUID) -> LocationORM | None:
        location = await self.uow.locations.get_by_id(
            location_id, options=_WITH_ADDRESS
        )
        if location is None:
            raise LocationNotExistsException()
        return location

    @required_transaction
    async def _find_address_proxy(self, address_id: UUID) -> LocationORM | None:
        stmt = (
            select(LocationORM)
            .where(
                LocationORM.address_id == address_id,
                LocationORM.name.is_(None),
            )
            .options(*_WITH_ADDRESS)
        )
        return (await self.uow.session.execute(stmt)).unique().scalar_one_or_none()

    @required_transaction
    async def _ensure_address_proxy(
        self, address_id: UUID
    ) -> tuple[LocationORM, bool]:
        address_exists = await self.uow.session.scalar(
            select(exists().where(AddressORM.id == address_id))
        )
        if not address_exists:
            raise AddressNotExistsException()
        created = (
            await self.uow.locations.insert_address_proxy(address_id)
            is not None
        )
        proxy = await self._find_address_proxy(address_id)
        return proxy, created

    @required_transaction
    async def _update(
        self, location_id: UUID, location_data: dict, *, flush: bool = False
    ) -> LocationORM:
        location = await self.uow.locations.update_one(
            location_id, location_data, flush
        )
        if location is None:
            raise LocationNotExistsException()
        return location

    @required_transaction
    async def _upsert(self, location_put: LocationPut) -> LocationORM:
        return await self.uow.locations.upsert(location_put.model_dump())

    @required_transaction
    async def _delete(self, location_id: UUID) -> None:
        await self.uow.locations.delete_one(location_id)

    async def create(self, location_create: LocationCreate) -> LocationRead:
        if location_create.address_id and location_create.name is None:
            return await self.find_or_create_address_proxy(
                location_create.address_id
            )
        async with self.uow as uow:
            created = await self._create(location_create)
            result = LocationRead.model_validate(await self._read(created.id))
            await uow.commit()
        await on_location_created(
            [LocationData(id=result.id, name=result.display_name)]
        )
        return result

    async def read(self, location_id: UUID) -> LocationRead:
        async with self.uow:
            return LocationRead.model_validate(await self._read(location_id))

    async def patch(self, location_patch: LocationPatch) -> LocationRead:
        async with self.uow as uow:
            location_data = location_patch.model_dump()
            updated = await self._update(location_data.pop("id"), location_data)
            result = LocationRead.model_validate(await self._read(updated.id))
            await uow.commit()
        await on_location_updated(
            [LocationData(id=result.id, name=result.display_name)]
        )
        return result

    async def put(self, location_put: LocationPut) -> LocationRead:
        async with self.uow as uow:
            upserted = await self._upsert(location_put)
            result = LocationRead.model_validate(await self._read(upserted.id))
            await uow.commit()
        await on_location_updated(
            [LocationData(id=result.id, name=result.display_name)]
        )
        return result

    async def delete(self, location_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(location_id)
            await uow.commit()
        await on_location_deleted([location_id])

    async def search(
        self,
        filter: LocationFilter,
        page_params: PageParamV1 = PageParamV1(),
        near: Point | None = None,
    ) -> PageV1[LocationRead]:
        async with self.uow as uow:
            items, total = await uow.locations.search(
                filter, page_params, options=_WITH_ADDRESS, near=near
            )
            return PageV1(
                items=[LocationRead.model_validate(item) for item in items],
                pagination=PaginationV1(page=page_params.page, limit=page_params.limit, total=total),
            )

    async def search_in_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        page_params: PageParamV1 = PageParamV1(),
    ) -> PageV1[LocationRead]:
        async with self.uow as uow:
            items, total = await uow.locations.search_in_bbox(
                min_lat, min_lon, max_lat, max_lon, page_params
            )
            return PageV1(
                items=[LocationRead.model_validate(item) for item in items],
                pagination=PaginationV1(
                    page=page_params.page, limit=page_params.limit, total=total
                ),
            )

    async def find_or_create_address_proxy(self, address_id: UUID) -> LocationRead:
        """The "just this address, nothing more specific" case: a
        location with no name of its own, anchored purely to the address.
        Idempotent and race-safe -- concurrent calls for the same address
        resolve to one row (unique partial index + ON CONFLICT DO NOTHING)."""
        async with self.uow as uow:
            proxy, created = await self._ensure_address_proxy(address_id)
            result = LocationRead.model_validate(proxy)
            await uow.commit()
        if created:
            await on_location_created(
                [LocationData(id=result.id, name=result.display_name)]
            )
        return result

    async def create_from_address(
        self, address_id: UUID, name: str | None
    ) -> LocationRead:
        if name is None:
            return await self.find_or_create_address_proxy(address_id)
        return await self.create(
            LocationCreate(name=name, address_id=address_id, spot=None)
        )
