from typing import Annotated
from fastapi import APIRouter, Depends
from core.schema.pagination import SPage, SPageParam
from user.dependencies.user import get_user_uow
from user.schemas.user import CheckResponse, UserRead
from user.services.user import UserService
from user.uow.user import UserUOW

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get("/check/{username}")
async def check_username(
    uow: Annotated[UserUOW, Depends(get_user_uow)], username: str
) -> CheckResponse:
    return CheckResponse(
        username=username,
        exists=(await UserService(uow).check_username(username)),
    )


@router.get("")
async def get_many(
    uow: Annotated[UserUOW, Depends(get_user_uow)],
    page_param=Depends(SPageParam),
) -> SPage[UserRead]:
    return await UserService(uow).get_many(page_param)
