from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from event.api.v1.schema.event import (
    EventCreate,
    EventPatch,
    EventPatchData,
    EventPut,
    EventPutData,
    EventRead,
)
from event.api.v1.schema.stage import (
    StageRead,
)
from event.dependency.event import EventUOWDep
from event.dependency.stage import StageUOWDep
from event.filter.event import EventFilter
from event.filter.stage import StageFilter
from event.service.event import EventService
from event.service.stage import StageService

router = APIRouter(prefix="/events", tags=["event"])

logger = getLogger(__name__)


@router.get(
    "",
    responses={
        **auth_responses(),
    },
)
async def get_events(
    uow: EventUOWDep,
    user: UserJWTDep,
    filter: EventFilter = FilterDepends(EventFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[EventRead]:
    return PageV1[EventRead].from_dto(
        await EventService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.post(
    "",
    responses={
        **auth_responses(),
    },
)
async def create_event(
    event: EventCreate, user: SuperUserJWTDep, uow: EventUOWDep
) -> EventRead:
    return EventRead.from_dto(await EventService(uow).create(event.to_dto()))


@router.get(
    "/{event_id}",
    responses={
        **auth_responses(),
        **entity_not_found_responses("event"),
    },
)
async def get_event(
    event_id: UUID, user: UserJWTDep, uow: EventUOWDep
) -> EventRead:
    return EventRead.from_dto(await EventService(uow).read(event_id))


@router.put(
    "/{event_id}",
    responses={
        **auth_responses(),
        **entity_not_found_responses("event"),
    },
)
async def put_event(
    event_id: UUID, event: EventPutData, user: SuperUserJWTDep, uow: EventUOWDep
) -> EventRead:
    result = await EventService(uow).put(
        EventPut(id=event_id, **event.model_dump()).to_dto()
    )
    return EventRead.from_dto(result)


@router.patch(
    "/{event_id}",
    responses={
        **auth_responses(),
        **entity_not_found_responses("event"),
    },
)
async def patch_event(
    event_id: UUID,
    event: EventPatchData,
    user: SuperUserJWTDep,
    uow: EventUOWDep,
) -> EventRead:
    result = await EventService(uow).patch(
        EventPatch(id=event_id, **event.model_dump()).to_dto()
    )
    return EventRead.from_dto(result)


@router.get(
    "/{event_id}/stages",
    responses={
        **auth_responses(),
        **entity_not_found_responses("event"),
    },
)
async def get_event_stages(
    event_id: UUID,
    uow: StageUOWDep,
    user: UserJWTDep,
    filter: StageFilter = FilterDepends(StageFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[StageRead]:
    filter.event_id = event_id
    return PageV1[StageRead].from_dto(
        await StageService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.delete(
    "/{event_id}",
    responses={
        **auth_responses(),
        **entity_not_found_responses("event"),
    },
)
async def delete_event(
    event_id: UUID, user: SuperUserJWTDep, uow: EventUOWDep
) -> None:
    await EventService(uow).delete(event_id)
