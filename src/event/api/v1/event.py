from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.pagination import SPage, SPageParam
from event.dependency.event import EventUOWDep
from event.dependency.stage import StageUOWDep
from event.filter.event import EventFilter
from event.filter.stage import StageFilter
from ...schema.event import (
    EventCreate,
    EventPatch,
    EventPatchData,
    EventPut,
    EventPutData,
    EventRead,
)
from ...schema.stage import StageRead
from event.service.event import EventService
from event.service.stage import StageService

router = APIRouter(prefix="/events", tags=["event"])

logger = getLogger(__name__)


@router.get("")
async def get_events(
    uow: EventUOWDep,
    user: UserJWTDep,
    filter: EventFilter = FilterDepends(EventFilter),
    page_param=Depends(SPageParam),
) -> SPage[EventRead]:
    return await EventService(uow).search(filter, page_param)


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


@router.get("/{event_id}/stages")
async def get_event_stages(
    event_id: UUID,
    uow: StageUOWDep,
    user: UserJWTDep,
    filter: StageFilter = FilterDepends(StageFilter),
    page_param=Depends(SPageParam),
) -> SPage[StageRead]:
    filter.event_id = event_id
    return await StageService(uow).search(filter, page_param)


@router.delete("/{event_id}")
async def delete_event(
    event_id: UUID, user: SuperUserJWTDep, uow: EventUOWDep
) -> None:
    await EventService(uow).delete(event_id)
