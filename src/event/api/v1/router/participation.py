from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from event.api.v1.schema.participation import (
    ParticipationCreate,
    ParticipationPatch,
    ParticipationPatchData,
    ParticipationPut,
    ParticipationPutData,
    ParticipationRead,
)
from event.dependency.participation import ParticipationUOWDep
from event.filter.participation import ParticipationFilter
from event.service.participation import ParticipationService

router = APIRouter(prefix="/participations", tags=["participation"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_participations(
    uow: ParticipationUOWDep,
    user: UserJWTDep,
    filter: ParticipationFilter = FilterDepends(ParticipationFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
) -> PageV1[ParticipationRead]:
    return PageV1[ParticipationRead].from_dto(
        await ParticipationService(uow).search(filter.to_dto(), page_param.to_dto())
    )


@router.post("", responses={**auth_responses()})
async def create_participation(
    participation: ParticipationCreate,
    user: SuperUserJWTDep,
    uow: ParticipationUOWDep,
) -> ParticipationRead:
    return ParticipationRead.from_dto(
        await ParticipationService(uow).create(participation.to_dto())
    )


@router.get(
    "/{participation_id}",
    responses={
        **auth_responses(),
        **entity_not_found_responses("participation"),
    },
)
async def get_participation(
    participation_id: UUID,
    user: UserJWTDep,
    uow: ParticipationUOWDep,
) -> ParticipationRead:
    return ParticipationRead.from_dto(
        await ParticipationService(uow).read(participation_id)
    )


@router.put(
    "/{participation_id}",
    responses={
        **auth_responses(),
        **entity_not_found_responses("participation"),
    },
)
async def put_participation(
    participation_id: UUID,
    participation: ParticipationPutData,
    user: SuperUserJWTDep,
    uow: ParticipationUOWDep,
) -> ParticipationRead:
    result = await ParticipationService(uow).put(
        ParticipationPut(
            id=participation_id, **participation.model_dump()
        ).to_dto()
    )
    return ParticipationRead.from_dto(result)


@router.patch(
    "/{participation_id}",
    responses={
        **auth_responses(),
        **entity_not_found_responses("participation"),
    },
)
async def patch_participation(
    participation_id: UUID,
    participation: ParticipationPatchData,
    user: SuperUserJWTDep,
    uow: ParticipationUOWDep,
) -> ParticipationRead:
    result = await ParticipationService(uow).patch(
        ParticipationPatch(
            id=participation_id, **participation.model_dump()
        ).to_dto()
    )
    return ParticipationRead.from_dto(result)


@router.delete(
    "/{participation_id}",
    responses={
        **auth_responses(),
        **entity_not_found_responses("participation"),
    },
)
async def delete_participation(
    participation_id: UUID,
    user: SuperUserJWTDep,
    uow: ParticipationUOWDep,
) -> None:
    await ParticipationService(uow).delete(participation_id)
