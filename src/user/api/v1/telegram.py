from fastapi import APIRouter, Depends

from core.dependencies.auth import ActiveUserJWTDep
from core.schema.error import auth_responses
from user.dependencies.user import get_user_service
from user.schemas.user import TelegramLinkTokenRead
from user.services.user import UserService

router = APIRouter(prefix="/v1/users/me/telegram", tags=["telegram"])


@router.post("/link-token", responses={**auth_responses()})
async def create_telegram_link_token(
    user: ActiveUserJWTDep,
    user_service: UserService = Depends(get_user_service),
) -> TelegramLinkTokenRead:
    """Mints a short-lived deep link (``t.me/<bot>?start=<token>``) the caller
    can open to link their Telegram profile to this AlmaEventFlow account."""
    return await user_service.create_telegram_link_token(user.person_id)
