from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from core.dependencies.auth import UserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_403,
    entity_not_found_responses,
)
from core.schema.user import UserJWT
from event.api.v2.schema.collective_profile import CollectiveProfileRead
from event.api.v2.schema.matrix import (
    AttendanceMatrix,
    CollectiveEvents,
    CollectiveRoster,
    MatrixParams,
)
from event.api.v2.schema.member_profile import MemberProfileParams
from event.dependency.collective_profile import CollectiveProfileUOWDep
from event.dependency.principal import verify_collective_principal
from event.dependency.view import ViewUOWDep
from event.dto.member_profile import ProfileViewerDTO
from event.dto.principal import CollectivePrincipalDTO
from event.service.collective_profile import CollectiveProfileService
from event.service.collective_view import CollectiveViewService

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
    viewer = ProfileViewerDTO(
        person_id=user.person_id, is_superuser=user.is_superuser
    )
    return CollectiveProfileRead.from_dto(
        await CollectiveProfileService(uow).read(
            collective_id, period.to_dto(), viewer
        )
    )


@router.get(
    "/{collective_id}/roster",
    responses={
        **auth_responses(),
        **detail_403(ErrorCode.NOT_COLLECTIVE_PRINCIPAL),
    },
)
async def get_collective_roster(
    collective_id: UUID,
    uow: ViewUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(
        verify_collective_principal
    ),
) -> CollectiveRoster:
    """The members with their names and roles, and the roles of the collective.
    For its leader and superusers."""
    return CollectiveRoster.from_dto(
        await CollectiveViewService(uow).roster(collective_id)
    )


@router.get(
    "/{collective_id}/events",
    responses={
        **auth_responses(),
        **detail_403(ErrorCode.NOT_COLLECTIVE_PRINCIPAL),
    },
)
async def get_collective_events(
    collective_id: UUID,
    uow: ViewUOWDep,
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(
        verify_collective_principal
    ),
) -> CollectiveEvents:
    """Every event the collective takes part in, in any status, a template too.
    For its leader and superusers."""
    return CollectiveEvents.from_dto(
        await CollectiveViewService(uow).events(collective_id)
    )


@router.get(
    "/{collective_id}/attendance-matrix",
    responses={
        **auth_responses(),
        **detail_403(ErrorCode.NOT_COLLECTIVE_PRINCIPAL),
    },
)
async def get_attendance_matrix(
    collective_id: UUID,
    uow: ViewUOWDep,
    params: Annotated[MatrixParams, Query()],
    _: tuple[CollectivePrincipalDTO, UserJWT] = Depends(
        verify_collective_principal
    ),
) -> AttendanceMatrix:
    """The roster against a window of the collective's events with every declared
    place: the table of the leader's panel in one answer. Keyset paging as in the
    feed."""
    return AttendanceMatrix.from_dto(
        await CollectiveViewService(uow).matrix(collective_id, params.to_dto())
    )
