from fastapi import APIRouter
from pydantic import BaseModel

from core.dependencies.auth import ActiveUserJWTDep
from core.schema.error import ErrorCode, auth_responses, detail_response
from fastapi import status

from notify.config.settings import settings
from notify.exc import WebPushNotConfiguredException

router = APIRouter(prefix="/webpush", tags=["notify"])


class VapidPublicKey(BaseModel):
    public_key: str


@router.get(
    "/vapid-public-key",
    responses={
        **auth_responses(),
        **detail_response(
            status.HTTP_503_SERVICE_UNAVAILABLE, ErrorCode.WEBPUSH_NOT_CONFIGURED
        ),
    },
)
async def get_vapid_public_key(user: ActiveUserJWTDep) -> VapidPublicKey:
    """Public VAPID key for ``PushManager.subscribe`` in the browser."""
    if not settings.vapid_configured:
        raise WebPushNotConfiguredException()
    return VapidPublicKey(public_key=settings.vapid_public_key)
