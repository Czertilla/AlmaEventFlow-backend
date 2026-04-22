from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from event.dependency.event import EventUOWDep
from ...schema.event import (
    EventCreate,
    EventPatch,
    EventPatchData,
    EventPut,
    EventPutData,
    EventRead,
)
from event.service.event import EventService

router = APIRouter(prefix="/events", tags=["event"])

logger = getLogger(__name__)


@router.post("")
async def create_event(
    event: EventCreate, user: SuperUserJWTDep, uow: EventUOWDep
) -> EventRead:
    return await EventService(uow).create(event)


@router.get("/{event_id}")
async def get_event(
    event_id: UUID, user: UserJWTDep, uow: EventUOWDep
) -> EventRead:
    return await EventService(uow).read(event_id)


@router.put("/{event_id}")
async def put_event(
    event_id: UUID, event: EventPutData, user: SuperUserJWTDep, uow: EventUOWDep
) -> EventRead:
    return await EventService(uow).put(
        EventPut(id=event_id, **event.model_dump())
    )


@router.patch("/{event_id}")
async def patch_event(
    event_id: UUID,
    event: EventPatchData,
    user: SuperUserJWTDep,
    uow: EventUOWDep,
) -> EventRead:
    return await EventService(uow).patch(
        EventPatch(id=event_id, **event.model_dump())
    )


@router.delete("/{event_id}")
async def delete_event(
    event_id: UUID, user: SuperUserJWTDep, uow: EventUOWDep
) -> None:
    await EventService(uow).delete(event_id)
