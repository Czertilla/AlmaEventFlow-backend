from typing import Annotated

from fastapi import Depends

from core.dependencies.auth import UserJWTDep
from event.dependency.member import MemberUOWDep
from event.dto.scope import CollectiveScopeDTO
from event.service.visibility import VisibilityService


async def get_collective_scope(
    user: UserJWTDep, uow: MemberUOWDep
) -> CollectiveScopeDTO:
    return await VisibilityService(uow).collective_scope(
        user.person_id, user.is_superuser
    )


CollectiveScopeDep = Annotated[CollectiveScopeDTO, Depends(get_collective_scope)]
