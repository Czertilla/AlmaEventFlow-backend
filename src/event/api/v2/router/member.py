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
from event.api.v2.schema.member_profile import MemberProfileParams, MemberProfileRead
from event.dependency.member_profile import MemberProfileUOWDep
from event.dto.member_profile import ProfileViewerDTO
from event.service.member_profile import MemberProfileService

router = APIRouter(prefix="/members", tags=["member"])


@router.get(
    "/{member_id}/profile",
    responses={
        **auth_responses(),
        **entity_not_found_responses("member"),
        **detail_403(ErrorCode.NOT_COLLECTIVE_MEMBER),
    },
)
async def get_member_profile(
    member_id: UUID,
    user: UserJWTDep,
    uow: MemberProfileUOWDep,
    period: Annotated[MemberProfileParams, Query()],
) -> MemberProfileRead:
    """A member's card with attendance statistics.

    Open to the leader of the member's collective, the collective's active
    members and superusers (``403 NOT_COLLECTIVE_MEMBER`` otherwise).
    """
    viewer = ProfileViewerDTO(person_id=user.person_id, is_superuser=user.is_superuser)
    return MemberProfileRead.from_dto(
        await MemberProfileService(uow).read(member_id, period.to_dto(), viewer)
    )
