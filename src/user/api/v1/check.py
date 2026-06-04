from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from core.dependencies.auth import SuperUserJWTDep
from core.schema.error import auth_responses
from core.schema.pagination import SPage, SPageParam
from user.dependencies.user import get_user_uow
from user.filter.user import UserFilter
from user.schemas.user import (
    CheckResponse,
    InviteTokenCreate,
    InviteTokenRead,
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
