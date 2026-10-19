from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from core.dependencies.auth import UserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_403,
    entity_not_found_responses,
)
from event.api.v2.schema.collective_profile import CollectiveProfileRead
from event.api.v2.schema.member_profile import MemberProfileParams
from event.dependency.collective_profile import CollectiveProfileUOWDep
from event.dto.member_profile import ProfileViewerDTO
from event.service.collective_profile import CollectiveProfileService

router = APIRouter(prefix="/collectives", tags=["collective"])


@router.get(
    "/{collective_id}/profile",
    responses={
        **auth_responses(),
        **entity_not_found_responses("collective"),
        **detail_403(ErrorCode.NOT_COLLECTIVE_MEMBER),
    },
)
async def get_collective_profile(
    collective_id: UUID,
    user: UserJWTDep,
    uow: CollectiveProfileUOWDep,
    period: Annotated[MemberProfileParams, Query()],
) -> CollectiveProfileRead:
    """A collective's card with the attendance of its whole roster.

    Open to the leader, the collective's active members and superusers
    (``403 NOT_COLLECTIVE_MEMBER`` otherwise).
    """
    viewer = ProfileViewerDTO(person_id=user.person_id, is_superuser=user.is_superuser)
    return CollectiveProfileRead.from_dto(
        await CollectiveProfileService(uow).read(collective_id, period.to_dto(), viewer)
    )
