from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi_users import models

from user.services.auth import get_jwt_strategy
from user.services.user import UserService
from user.utils.cookie import set_refresh_cookie, set_session_cookie
from user.utils.request import extract_device_info, extract_ip


async def finish_login(
    request: Request, user: models.UP, user_service: UserService
) -> JSONResponse:
    """Issues an access token plus a fresh session/refresh-token pair for an
    already-authenticated ``user``. Shared by every login path (password,
    Telegram widget, ...) so cookie handling and the login notification stay
    in one place."""
    strategy = get_jwt_strategy()
    access_token = await strategy.write_token(user)

    device_info = extract_device_info(request)
    ip_address = extract_ip(request)

    async with user_service.uow:
        raw_refresh, _, _, session_id = await user_service._create_session(
            user.id, device_info=device_info, ip_address=ip_address
        )
        response = JSONResponse(
            content={
                "access_token": access_token,
                "token_type": "bearer",
            }
        )
        set_refresh_cookie(response, raw_refresh)
        set_session_cookie(response, session_id)
        response._refresh_token_created = True
        await user_service.on_after_login(user, request, response)
        await user_service.uow.commit()
    return response
