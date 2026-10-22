from profile.api.v2.schema.invite import (
    InviteTokenCreate,
    InviteTokenData,
    InviteTokenRead,
)
from profile.dependency.person import PersonUOWDep
from profile.service.invite import InviteService
from uuid import UUID

from fastapi import APIRouter

from core.dependencies.auth import SuperUserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_404,
    detail_response,
    error_response,
)

router = APIRouter(prefix="/persons", tags=["person", "invite"])


@router.post(
    "/{person_id}/invite",
    responses={
        **auth_responses(),
        **error_response(
            400,
            "The person already has an account",
            {ErrorCode.PERSON_ALREADY_HAS_ACCOUNT: {}},
        ),
        **detail_404(ErrorCode.PERSON_NOT_FOUND),
        **detail_response(503, ErrorCode.INVITE_SIGNING_NOT_CONFIGURED),
    },
)
async def create_invite(
    person_id: UUID,
    data: InviteTokenData,
    user: SuperUserJWTDep,
    uow: PersonUOWDep,
) -> InviteTokenRead:
    """A token that lets its bearer register an account for the person, 
    or attach the person to an account they already have."""
    return InviteTokenRead.from_dto(
        await InviteService(uow).create(
            InviteTokenCreate(person_id=person_id, **data.model_dump()).to_dto()
        )
    )
