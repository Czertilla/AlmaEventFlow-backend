from fastapi import APIRouter

from core.dependencies.auth import ActiveUserJWTDep
from core.enum.notify import NotificationCategory
from core.schema.error import auth_responses
from core.schema.message.notify import NotificationRequest

from notify.dependency.notify import NotifyUOWDep
from notify.service.dispatch import NotificationService

router = APIRouter(prefix="/test", tags=["notify"])


@router.post("", responses={**auth_responses()})
async def send_test_notification(
    user: ActiveUserJWTDep,
    uow: NotifyUOWDep,
) -> dict[str, str]:
    """Sends a test notification to the current user via all enabled transports."""
    await NotificationService(uow).dispatch(
        NotificationRequest(
            user_ids=[user.id],
            category=NotificationCategory.system,
            title="Тестовое уведомление",
            body="Если вы это видите — доставка уведомлений работает.",
        )
    )
    return {"status": "dispatched"}
