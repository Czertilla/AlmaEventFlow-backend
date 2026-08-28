from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.pagination import SPage, SPageParam
from event.dependency.stage import StageUOWDep
from event.exc.event import StageNotExistsException
from event.filter.stage import StageFilter
from event.schema.stage import (
    StageCreate,
    StagePatch,
    StagePatchData,
    StagePut,
    StagePutData,
    StageRead,
)
from event.service.notification import notify_collective_chats
from event.service.stage import StageService

router = APIRouter(prefix="/stages", tags=["stage"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_stages(
    uow: StageUOWDep,
    user: UserJWTDep,
    filter: StageFilter = FilterDepends(StageFilter),
    page_param=Depends(SPageParam),
) -> SPage[StageRead]:
    return await StageService(uow).search(filter, page_param)


@router.post("", responses={**auth_responses()})
async def create_stage(
    stage: StageCreate, user: SuperUserJWTDep, uow: StageUOWDep
) -> StageRead:
    result = await StageService(uow).create(stage)
    async with uow as scope:
        await notify_collective_chats(scope, event_ids=[result.event_id])
    return result


@router.get("/{stage_id}", responses={**auth_responses(), **entity_not_found_responses("stage")})
async def get_stage(
    stage_id: UUID, user: UserJWTDep, uow: StageUOWDep
) -> StageRead:
    return await StageService(uow).read(stage_id)


@router.put("/{stage_id}", responses={**auth_responses(), **entity_not_found_responses("stage")})
async def put_stage(
    stage_id: UUID, stage: StagePutData, user: SuperUserJWTDep, uow: StageUOWDep
) -> StageRead:
    result = await StageService(uow).put(StagePut(id=stage_id, **stage.model_dump()))
    async with uow as scope:
        await notify_collective_chats(scope, event_ids=[result.event_id])
    return result


@router.patch("/{stage_id}", responses={**auth_responses(), **entity_not_found_responses("stage")})
async def patch_stage(
    stage_id: UUID, stage: StagePatchData, user: SuperUserJWTDep, uow: StageUOWDep
) -> StageRead:
    result = await StageService(uow).patch(
        StagePatch(id=stage_id, **stage.model_dump())
    )
    async with uow as scope:
        await notify_collective_chats(scope, event_ids=[result.event_id])
    return result


@router.delete("/{stage_id}", responses={**auth_responses(), **entity_not_found_responses("stage")})
async def delete_stage(
    stage_id: UUID, user: SuperUserJWTDep, uow: StageUOWDep
) -> None:
    async with uow as scope:
        stage = await scope.stages.get_by_id(stage_id)
    if stage is None:
        raise StageNotExistsException()
    await StageService(uow).delete(stage_id)
    async with uow as scope:
        await notify_collective_chats(scope, event_ids=[stage.event_id])