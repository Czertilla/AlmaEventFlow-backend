from logging import getLogger

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from user.config.settings import settings
from user.dependencies.user import get_user_service
from user.services.user import UserService
from user.services.auth import (
    get_jwt_strategy,
    set_access_cookie,
    set_refresh_cookie,
    unset_access_cookie,
    unset_refresh_cookie,
)
from user.schemas.user import UserRead

logger = getLogger(__name__)

router = APIRouter()


@router.post("/login")
async def login(
    request: Request,
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.authenticate(credentials)
    if user is None or not user.is_active:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="LOGIN_BAD_CREDENTIALS")

    strategy = get_jwt_strategy()
    access_token = await strategy.write_token(user)

    raw_refresh, _ = await user_service.create_session(user.id)

    response = JSONResponse(
        content={
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            "refresh_expires_in": settings.REFRESH_TOKEN_EXPIRE_SECONDS,
            "user": UserRead.model_validate(user).model_dump(mode="json"),
        }
    )

    set_access_cookie(response, access_token)
    set_refresh_cookie(response, raw_refresh)
    response._refresh_token_created = True

    await user_service.on_after_login(user, request, response)
    return response


@router.post("/refresh")
async def refresh(
    request: Request,
    user_service: UserService = Depends(get_user_service),
):
    raw_refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw_refresh:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Refresh token missing")

    result = await user_service.rotate_session(raw_refresh)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_raw_refresh, _, user_id = result
    user = await user_service.get(user_id)

    strategy = get_jwt_strategy()
    access_token = await strategy.write_token(user)

    response = JSONResponse(
        content={
            "access_token": access_token,
            "refresh_token": new_raw_refresh,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            "refresh_expires_in": settings.REFRESH_TOKEN_EXPIRE_SECONDS,
        }
    )

    set_access_cookie(response, access_token)
    set_refresh_cookie(response, new_raw_refresh)
    return response


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user_service: UserService = Depends(get_user_service),
):
    raw_refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if raw_refresh:
        await user_service.revoke_session(raw_refresh)

    unset_access_cookie(response)
    unset_refresh_cookie(response)

    response.status_code = status.HTTP_204_NO_CONTENT
    return response
