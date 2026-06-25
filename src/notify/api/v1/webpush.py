from fastapi import APIRouter
from pydantic import BaseModel

from core.dependencies.auth import ActiveUserJWTDep
from core.enum.notify import TransportTypeEnum
from core.schema.error import ErrorCode, auth_responses, detail_response
from fastapi import status

from notify.exc import WebPushNotConfiguredException
from notify.transport import registry
from notify.transport.webpush import WebPushTransport

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
    """``applicationServerKey`` for ``PushManager.subscribe`` in the browser,
    derived from the VAPID public key."""
    transport = registry.get(TransportTypeEnum.webpush)
    key = (
        transport.application_server_key()
        if isinstance(transport, WebPushTransport)
        else None
    )
    if not key:
        raise WebPushNotConfiguredException()
    return VapidPublicKey(public_key=key)
