from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import ActiveUserJWTDep, SuperUserJWTDep
from core.schema.error import (
    ErrorCode,
    auth_responses,
    detail_404,
    error_response,
)
from core.schema.pagination import SPage, SPageParam
from user.dependencies.user import get_user_uow
from user.filter.user import UserFilter
from user.schemas.user import (
    CheckResponse,
    InviteTokenCreate,
    InviteTokenRead,
    LinkInviteData,
    PersonLinkRequest,
    UserRead,
)
from user.services.user import UserService
from user.uow.user import UserUOW

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/check/{username}")
async def check_username(
    uow: Annotated[UserUOW, Depends(get_user_uow)],
    username: str,
) -> CheckResponse:
    return CheckResponse(
        username=username,
        exists=(await UserService(uow).check_username(username)),
    )


@router.get("")
async def get_many(
    uow: Annotated[UserUOW, Depends(get_user_uow)],
    filter: UserFilter = FilterDepends(UserFilter),
    page_param: SPageParam = Depends(SPageParam),
) -> SPage[UserRead]:
    return await UserService(uow).search(filter, page_param)


@router.post(
    "/invite",
    responses={
        **auth_responses(),
    },
)
async def create_invite_token(
    uow: Annotated[UserUOW, Depends(get_user_uow)],
    user: SuperUserJWTDep,
    invite_data: InviteTokenCreate,
) -> InviteTokenRead:
    return await UserService(uow).create_invite_token(invite_data)


@router.patch(
    "/{user_id}/person",
    responses={
        **auth_responses(),
        **error_response(
            400,
            "Person already linked, or does not exist",
            {
                ErrorCode.PERSON_ALREADY_HAS_ACCOUNT: {},
                ErrorCode.INVITE_PERSON_NOT_FOUND: {},
            },
        ),
        **detail_404(ErrorCode.USER_NOT_FOUND),
    },
)
async def link_person(
    uow: Annotated[UserUOW, Depends(get_user_uow)],
    user_id: UUID,
    payload: PersonLinkRequest,
    admin: SuperUserJWTDep,
) -> UserRead:
    """Admin-only: attaches an existing profile person to an existing
    account, for cases the invite-token flow doesn't cover (account created
    first, or re-linking to a different person)."""
    return await UserService(uow).admin_link_person(user_id, payload.person_id)


@router.post(
    "/me/link-invite",
    responses={
        **auth_responses(),
        **error_response(
            400,
            "Invite token invalid/expired, or person/account already linked",
            {
                ErrorCode.INVITE_TOKEN_INVALID: {},
                ErrorCode.INVITE_TOKEN_EXPIRED: {},
                ErrorCode.PERSON_ALREADY_HAS_ACCOUNT: {},
                ErrorCode.ACCOUNT_ALREADY_LINKED: {},
            },
        ),
    },
)
async def link_invite(
    uow: Annotated[UserUOW, Depends(get_user_uow)],
    user: ActiveUserJWTDep,
    payload: LinkInviteData,
) -> UserRead:
    """Self-service: an already-authenticated user opening an invite link
    confirms attaching that invite's person to their own account."""
    return await UserService(uow).link_invite(user.id, payload.token)
