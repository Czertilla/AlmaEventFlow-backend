from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from core.schema.error import ErrorCode, auth_responses, detail_403
from core.schema.user import UserJWT
from event.api.v2.schema.location import RecentLocationRead
from event.dependency.location import LocationUOWDep
from event.dependency.principal import verify_collective_principal
from event.dto.principal import CollectivePrincipalDTO
from event.service.location import LocationService

router = APIRouter(prefix="/collectives", tags=["location"])


@router.get(
    "/{collective_id}/recent-locations",
    responses={**auth_responses(), **detail_403(ErrorCode.NOT_COLLECTIVE_PRINCIPAL)},
)
async def get_recent_locations(
    collective_id: UUID,
    uow: LocationUOWDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(verify_collective_principal),
) -> list[RecentLocationRead]:
    """Where the collective held its events lately, the latest first.

    A place counts from the time its event was last edited (created, when it
    never was). For the leader of the collective and superusers; meant to
    seed a place picker, the ids are read from geo.
    """
    return [
        RecentLocationRead.from_dto(recent)
        for recent in await LocationService(uow).recent(collective_id, limit)
    ]
