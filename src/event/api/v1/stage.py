from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from event.dependency.stage import StageUOWDep
from event.schema.stage import (
    StageCreate,
    StagePatch,
    StagePut,
    StageRead,
)
from event.service.stage import StageService

router = APIRouter(prefix="/stages", tags=["stage"])

logger = getLogger(__name__)


@router.post("/new")
async def create_stage(
    stage: StageCreate, user: SuperUserJWTDep, uow: StageUOWDep
) -> StageRead:
    return await StageService(uow).create(stage)


@router.get("/{stage_id}")
async def get_stage(
    stage_id: UUID, user: UserJWTDep, uow: StageUOWDep
) -> StageRead:
    return await StageService(uow).read(stage_id)


@router.put("/{stage_id}")
async def put_stage(
    stage_id: UUID, stage: StagePut, user: SuperUserJWTDep, uow: StageUOWDep
) -> StageRead:
    return await StageService(uow).put(stage)


@router.patch("/{stage_id}")
async def patch_stage(
    stage_id: UUID, stage: StagePatch, user: SuperUserJWTDep, uow: StageUOWDep
) -> StageRead:
    return await StageService(uow).patch(stage)


@router.delete("/{stage_id}")
async def delete_stage(
    stage_id: UUID, user: SuperUserJWTDep, uow: StageUOWDep
) -> None:
    await StageService(uow).delete(stage_id)