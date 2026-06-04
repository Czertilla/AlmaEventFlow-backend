from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.pagination import SPage, SPageParam
from event.dependency.stage import StageUOWDep
from event.filter.stage import StageFilter
from event.schema.stage import (
    StageCreate,
    StagePatch,
    StagePatchData,
    StagePut,
    StagePutData,
    StageRead,
)
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
    return await StageService(uow).create(stage)


@router.get("/{stage_id}", responses={**auth_responses(), **entity_not_found_responses("stage")})
async def get_stage(
    stage_id: UUID, user: UserJWTDep, uow: StageUOWDep
) -> StageRead:
    return await StageService(uow).read(stage_id)


@router.put("/{stage_id}", responses={**auth_responses(), **entity_not_found_responses("stage")})
async def put_stage(
    stage_id: UUID, stage: StagePutData, user: SuperUserJWTDep, uow: StageUOWDep
) -> StageRead:
    return await StageService(uow).put(StagePut(id=stage_id, **stage.model_dump()))


@router.patch("/{stage_id}", responses={**auth_responses(), **entity_not_found_responses("stage")})
async def patch_stage(
    stage_id: UUID, stage: StagePatchData, user: SuperUserJWTDep, uow: StageUOWDep
) -> StageRead:
    return await StageService(uow).patch(StagePatch(id=stage_id, **stage.model_dump()))


@router.delete("/{stage_id}", responses={**auth_responses(), **entity_not_found_responses("stage")})
async def delete_stage(
    stage_id: UUID, user: SuperUserJWTDep, uow: StageUOWDep
) -> None:
    await StageService(uow).delete(stage_id)