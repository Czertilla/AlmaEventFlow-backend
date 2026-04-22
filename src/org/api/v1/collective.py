from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from org.dependency.collective import CollectiveUOWDep
from org.schema.collective import (
    CollectiveCreate,
    CollectivePatch,
    CollectivePatchData,
    CollectivePut,
    CollectivePutData,
    CollectiveRead,
)
from org.service.collective import CollectiveService

router = APIRouter(prefix="/collectives", tags=["collective"])

logger = getLogger(__name__)

@router.get("/{collective_id}")
async def get_collective(
    collective_id: UUID, user: UserJWTDep, uow: CollectiveUOWDep
) -> CollectiveRead:
    return await CollectiveService(uow).read(collective_id)

@router.post("/new")
async def create_collective(
    collective: CollectiveCreate,
    user: SuperUserJWTDep,
    uow: CollectiveUOWDep,
) -> CollectiveRead:
    return await CollectiveService(uow).create(collective)

@router.put("/{collective_id}")
async def put_collective(
    collective_id: UUID,
    collective: CollectivePutData,
    user: SuperUserJWTDep,
    uow: CollectiveUOWDep,
) -> CollectiveRead:
    return await CollectiveService(uow).put(
        CollectivePut(id=collective_id, **collective.model_dump())
    )

@router.patch("/{collective_id}")
async def patch_collective(
    collective_id: UUID,
    collective: CollectivePatchData,
    user: SuperUserJWTDep,
    uow: CollectiveUOWDep,
) -> CollectiveRead:
    return await CollectiveService(uow).patch(
        CollectivePatch(id=collective_id, **collective.model_dump())
    )

@router.delete("/{collective_id}")
async def delete_collective(
    collective_id: UUID, user: SuperUserJWTDep, uow: CollectiveUOWDep
) -> None:
    await CollectiveService(uow).delete(collective_id)