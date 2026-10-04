from uuid import UUID

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from user.dto.user import UserDTO
from user.service.user import UserService
from user.utils.cookie import set_refresh_cookie, set_session_cookie
from user.utils.jwt import AccessStrategy
from user.utils.request import extract_device_info, extract_ip


async def start_session(
    request: Request,
    response: Response,
    user_id: UUID,
    user_service: UserService,
) -> None:
    device_info = extract_device_info(request)
    tokens = await user_service.open_session(
        user_id, device_info=device_info, ip_address=extract_ip(request)
    )
    set_refresh_cookie(response, tokens.refresh_token)
    set_session_cookie(response, tokens.session_id)
    await user_service.announce_login(user_id, device_info)


async def finish_login(
    request: Request,
    user: UserDTO,
    user_service: UserService,
    strategy: AccessStrategy,
) -> JSONResponse:
    response = JSONResponse(
        content={
            "access_token": await strategy.write_token(user),
            "token_type": "bearer",
        }
    )
    await start_session(request, response, user.id, user_service)
    return response
