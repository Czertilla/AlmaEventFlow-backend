from typing import Any

from fastapi import APIRouter, Depends, Request

from core.schema.error import ErrorCode, auth_responses, detail_400, detail_404
from core.utils.exc.http import VancedHTTPException
from user.config.settings import settings
from user.dependencies.user import get_user_service
from user.exceptions.user import TelegramAccountNotLinked
from user.schemas.user import TelegramWidgetAuth
from user.services.user import UserService
from user.utils.auth_response import finish_login
from user.utils.telegram_auth import verify_telegram_widget_payload

router = APIRouter(prefix="/v1/auth/telegram", tags=["auth"])


@router.get("/config")
async def get_telegram_login_config() -> dict[str, str | None]:
    """Public: lets the frontend render the Login Widget without duplicating
    the bot's public username in its own config."""
    return {"bot_username": settings.BOT_TG_USERNAME}


@router.post(
    "/login",
    responses={
        **detail_400(ErrorCode.TELEGRAM_AUTH_INVALID),
        **detail_404(ErrorCode.TELEGRAM_ACCOUNT_NOT_LINKED),
        **auth_responses(),
    },
)
async def login_with_telegram(
    payload: TelegramWidgetAuth,
    request: Request,
    user_service: UserService = Depends(get_user_service),
) -> dict[str, Any]:
    """Alternative to password login: verifies the signed payload from
    Telegram's Login Widget and looks up the AEF user already linked via the
    bot's ``/start`` deep-link flow. Never creates an account -- a payload for
    an unlinked Telegram id is rejected with ``TELEGRAM_ACCOUNT_NOT_LINKED``."""
    verify_telegram_widget_payload(payload.model_dump(mode="json"))
    user = await user_service.get_by_telegram_id(str(payload.id))
    if user is None:
        raise TelegramAccountNotLinked()
    if not user.is_active:
        raise VancedHTTPException(
            status_code=400, detail=ErrorCode.LOGIN_BAD_CREDENTIALS
        )
    return await finish_login(request, user, user_service)
