from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from event.dependency.participation import ParticipationUOWDep
from ...schema.participation import (
    ParticipationCreate,
    ParticipationPatch,
    ParticipationPatchData,
    ParticipationPut,
    ParticipationPutData,
    ParticipationRead,
)
from event.service.participation import ParticipationService

router = APIRouter(prefix="/participations", tags=["participation"])

logger = getLogger(__name__)


@router.post("")
async def create_participation(
    participation: ParticipationCreate,
    user: SuperUserJWTDep,
    uow: ParticipationUOWDep,
) -> ParticipationRead:
    return await ParticipationService(uow).create(participation)


@router.get("/{participation_id}")
async def get_participation(
    participation_id: UUID,
    user: UserJWTDep,
    uow: ParticipationUOWDep,
) -> ParticipationRead:
    return await ParticipationService(uow).read(participation_id)


@router.put("/{participation_id}")
async def put_participation(
    participation_id: UUID,
    participation: ParticipationPutData,
    user: SuperUserJWTDep,
    uow: ParticipationUOWDep,
) -> ParticipationRead:
    return await ParticipationService(uow).put(
        ParticipationPut(id=participation_id, **participation.model_dump())
    )


@router.patch("/{participation_id}")
async def patch_participation(
    participation_id: UUID,
    participation: ParticipationPatchData,
    user: SuperUserJWTDep,
    uow: ParticipationUOWDep,
) -> ParticipationRead:
    return await ParticipationService(uow).patch(
        ParticipationPatch(id=participation_id, **participation.model_dump())
    )


@router.delete("/{participation_id}")
async def delete_participation(
    participation_id: UUID,
    user: SuperUserJWTDep,
    uow: ParticipationUOWDep,
) -> None:
    await ParticipationService(uow).delete(participation_id)
