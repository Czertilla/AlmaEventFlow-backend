import asyncio
import json
from uuid import UUID

from uuid import UUID

from core.enum.mq import NotifyDeliveryQueue
from core.enum.notify import TransportTypeEnum
from core.schema.message.notify import WebPushDeliveryBatch

from notify.config.settings import settings
from notify.exc import WebPushClientInvalidException
from notify.schema.client import ClientTarget
from notify.schema.notification import NotificationContent
from notify.transport.base import DirectTransport, DeliveryDraft

try:
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover
    webpush = None
    WebPushException = Exception


_DEAD_STATUSES = {404, 410}


class WebPushDeliveryError(Exception):
    """Raised by ``WebPushTransport.push``. ``dead`` marks an endpoint that no
    longer exists (HTTP 404/410) and must be deactivated."""

    def __init__(self, detail: str, *, dead: bool = False) -> None:
        super().__init__(detail)
        self.detail = detail
        self.dead = dead


class WebPushTransport(DirectTransport):
    """Direct Web Push delivery via VAPID. The in-notify worker loads the
    delivery from the database, so the published task carries only ids."""

    type = TransportTypeEnum.webpush
    label = "Web Push"
    delivery_topic = NotifyDeliveryQueue.WEBPUSH

    def is_available(self) -> bool:
        return webpush is not None and settings.vapid_configured

    def batch_size(self) -> int:
        return settings.WEBPUSH_DELIVERY_BATCH_SIZE

    def validate_client_payload(self, payload: dict[str, str]) -> dict[str, str]:
        p256dh = payload.get("p256dh")
        auth = payload.get("auth")
        if not p256dh or not auth:
            raise WebPushClientInvalidException()
        return {"p256dh": p256dh, "auth": auth}

    def build_batch(
        self, notification_id: UUID, drafts: list[DeliveryDraft]
    ) -> WebPushDeliveryBatch:
        return WebPushDeliveryBatch(
            notification_id=notification_id,
            transport=self.type,
            delivery_ids=[draft.delivery_id for draft in drafts],
        )

    def _payload(self, content: NotificationContent) -> str:
        return json.dumps(
            {
                "title": content.title,
                "body": content.body,
                "url": content.action_url,
                "data": content.data,
            }
        )

    def _send(self, subscription: dict, data: str) -> None:
        webpush(
            subscription_info=subscription,
            data=data,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.WEB_PUSH_VAPID_SUBJECT},
        )

    async def push(
        self, client: ClientTarget, content: NotificationContent
    ) -> None:
        subscription = {
            "endpoint": client.endpoint,
            "keys": {
                "p256dh": client.payload.get("p256dh"),
                "auth": client.payload.get("auth"),
            },
        }
        try:
            await asyncio.to_thread(self._send, subscription, self._payload(content))
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            raise WebPushDeliveryError(
                str(exc), dead=status in _DEAD_STATUSES
            ) from exc
