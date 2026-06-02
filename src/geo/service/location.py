from logging import getLogger

from core.schema.pagination import SPage, SPageParam, SPagination
from core.service.base import BaseService, required_transaction

from geo.exc.location import LocationNotExistsException
from geo.filter.location import LocationFilter
from geo.models.location import LocationORM
from geo.schema.location import (
    LocationCreate,
    LocationPatch,
    LocationPut,
    LocationRead,
)
from geo.uow.location import LocationUOW

logger = getLogger()


class LocationService(BaseService[LocationUOW]):
    @required_transaction
    async def _create(self, location_create: LocationCreate) -> LocationORM:
        return await self.uow.locations.add_n_return(
            location_create.model_dump()
        )

    @required_transaction
    async def _read(self, location_id: int) -> LocationORM | None:
        location = await self.uow.locations.get_by_id(location_id)
        if location is None:
            raise LocationNotExistsException()
        return location

    @required_transaction
    async def _update(
        self, location_id: int, location_data: dict, *, flush: bool = False
    ) -> LocationORM:
        location = await self.uow.locations.update_one(
            location_id, location_data, flush
        )
        if location is None:
            raise LocationNotExistsException()
        return location

    async def create(self, location_create: LocationCreate) -> LocationRead:
        async with self.uow as uow:
            result = LocationRead.model_validate(
                await self._create(location_create)
            )
            await uow.commit()
        return result

    async def read(self, location_id: int) -> LocationRead:
        async with self.uow:
            return LocationRead.model_validate(await self._read(location_id))

    async def patch(self, location_patch: LocationPatch) -> LocationRead:
        async with self.uow as uow:
            location_data = location_patch.model_dump()
            result = LocationRead.model_validate(
                await self._update(location_data.pop("id"), location_data)
            )
            await uow.commit()
        return result

    async def put(self, location_put: LocationPut) -> LocationRead:
        async with self.uow as uow:
            result = LocationRead.model_validate(
                await self.uow.locations.upsert(location_put.model_dump())
            )
            await uow.commit()
        return result

    async def delete(self, location_id: int) -> None:
        async with self.uow as uow:
            await self.uow.locations.delete_one(location_id)
            await uow.commit()

    async def search(self, filter: LocationFilter, page_params: SPageParam = SPageParam()) -> SPage[LocationRead]:
        async with self.uow as uow:
            items, total = await uow.locations.search(filter, page_params)
            return SPage(
                items=[LocationRead.model_validate(item) for item in items],
                pagination=SPagination(page=page_params.page, limit=page_params.limit, total=total),
            )
