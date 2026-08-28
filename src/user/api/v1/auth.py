from logging import getLogger
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from core.schema.error import ErrorCode, ErrorModel
from core.utils.exc.http import VancedHTTPException
from user.config.settings import settings
from user.dependencies.user import get_user_service
from user.services.auth import get_jwt_strategy
from user.services.user import UserService
from user.utils.auth_response import finish_login
from user.utils.cookie import (
    set_refresh_cookie,
    set_session_cookie,
    unset_refresh_cookie,
    unset_session_cookie,
)
from user.utils.request import extract_device_info, extract_ip

logger = getLogger(__name__)

router = APIRouter()


@router.post(
    "/login",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorModel,
            "content": {
                "application/json": {
                    "examples": {
                        ErrorCode.LOGIN_BAD_CREDENTIALS.value: {
                            "summary": "Bad credentials or the user is inactive.",
                            "value": {"detail": ErrorCode.LOGIN_BAD_CREDENTIALS.value},
                        },
                    }
                }
            },
            "description": "Bad credentials or inactive user",
        },
    },
)
async def login(
    request: Request,
    credentials: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    user = await user_service.authenticate(credentials)
    if user is None or not user.is_active:
        raise VancedHTTPException(
            status_code=400, detail=ErrorCode.LOGIN_BAD_CREDENTIALS
        )
    return await finish_login(request, user, user_service)


@router.post(
    "/refresh",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorModel,
            "content": {
                "application/json": {
                    "examples": {
                        ErrorCode.REFRESH_TOKEN_MISSING.value: {
                            "summary": "Refresh token missing in cookies.",
                            "value": {"detail": ErrorCode.REFRESH_TOKEN_MISSING.value},
                        },
                        ErrorCode.INVALID_REFRESH_TOKEN.value: {
                            "summary": "Refresh token is invalid or expired.",
                            "value": {"detail": ErrorCode.INVALID_REFRESH_TOKEN.value},
                        },
                    }
                }
            },
            "description": "Missing or invalid refresh token",
        },
    },
)
async def refresh(
    request: Request,
    user_service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    raw_refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise VancedHTTPException(
            status_code=401, detail=ErrorCode.REFRESH_TOKEN_MISSING
        )

    result = await user_service.refresh_session(
        raw_refresh,
        device_info=extract_device_info(request),
        ip_address=extract_ip(request),
    )
    if result is None:
        raise VancedHTTPException(
            status_code=401, detail=ErrorCode.INVALID_REFRESH_TOKEN
        )
    new_raw_refresh, _, user_id, session_id = result

    user = await user_service.get(user_id)

    strategy = get_jwt_strategy()
    access_token = await strategy.write_token(user)

    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
        }
    )

    set_refresh_cookie(response, new_raw_refresh)
    set_session_cookie(response, session_id)
    return response


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def logout(
    request: Request,
    response: Response,
    user_service: UserService = Depends(get_user_service),
) -> Response:
    raw_refresh = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if raw_refresh:
        await user_service.revoke_session_by_token(raw_refresh)

    unset_refresh_cookie(response)
    unset_session_cookie(response)

    response.status_code = status.HTTP_204_NO_CONTENT
    return response
