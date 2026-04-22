from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction
from event.models.event import EventORM
from event.schema.event import (
    EventCreate,
    EventPatch,
    EventPut,
    EventRead,
)
from event.uow.event import EventUOW

logger = getLogger(__name__)


class EventService(BaseService[EventUOW]):
    @required_transaction
    async def _create(self, event_create: EventCreate) -> EventORM:
        event_data = event_create.model_dump()
        event = await self.uow.events.add_n_return(data=event_data)
        await self.uow.session.flush(objects=[event])
        return event

    @required_transaction
    async def _read(self, event_id: UUID) -> EventORM | None:
        event = await self.uow.events.get_by_id(event_id)
        return event

    @required_transaction
    async def _update(
        self, event_id: UUID, event_data: dict, *, flush: bool = False
    ) -> EventORM:
        event = await self.uow.events.update_one(event_id, event_data, flush)
        return event

    @required_transaction
    async def _delete(self, event_id: UUID) -> None:
        await self.uow.events.delete_one(event_id)

    async def create(self, event_create: EventCreate) -> EventRead:
        async with self.uow as uow:
            event = await self._create(event_create)
            result = EventRead.model_validate(event)
            await uow.commit()
        return result

    async def read(self, event_id: UUID) -> EventRead:
        async with self.uow:
            event = await self._read(event_id)
            return EventRead.model_validate(event)

    async def patch(self, event_patch: EventPatch) -> EventRead:
        async with self.uow as uow:
            event_data = event_patch.model_dump(exclude_unset=True)
            event = await self._update(event_patch.id, event_data)
            result = EventRead.model_validate(event)
            await uow.commit()
        return result

    async def put(self, event_put: EventPut) -> EventRead:
        async with self.uow as uow:
            event_data = event_put.model_dump()
            event_id = event_data.pop("id")
            event = await self._update(event_id, event_data)
            result = EventRead.model_validate(event)
            await uow.commit()
        return result

    async def delete(self, event_id: UUID) -> None:
        async with self.uow as uow:
            await self._delete(event_id)
            await uow.commit()
