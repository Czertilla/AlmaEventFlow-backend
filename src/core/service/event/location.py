from typing import Generic, TypeVar
from uuid import UUID
from core.service.base import BaseService, required_transaction
from core.uow.event.location import LocationAUOW
from core.schema.message.geo import LocationData, LocationDelete

UOW = TypeVar("UOW", bound=LocationAUOW)


class LocationEventService(BaseService[UOW], Generic[UOW]):
    @required_transaction
    async def _create(self, location: LocationData):
        await self.uow.locations.add_n_return(data=location.model_dump())

    @required_transaction
    async def _upsert(self, location: LocationData):
        await self.uow.locations.upsert(data=location.model_dump())

    @required_transaction
    async def _delete(self, location_id: UUID):
        await self.uow.locations.delete_one(location_id)

    async def create(self, locations: list[LocationData]) -> None:
        async with self.uow as uow:
            for location in locations:
                await self._create(location)
            await uow.commit()

    async def update(self, locations: list[LocationData]) -> None:
        async with self.uow as uow:
            for location in locations:
                await self._upsert(location)
            await uow.commit()

    async def delete(self, locations: list[LocationDelete]) -> None:
        async with self.uow as uow:
            for location in locations:
                await self._delete(location.id)
            await uow.commit()
