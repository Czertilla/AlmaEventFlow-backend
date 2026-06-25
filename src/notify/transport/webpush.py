import base64
from logging import getLogger
from uuid import UUID

import aiohttp
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
    load_pem_public_key,
)

from core.enum.mq import NotifyDeliveryQueue
from core.enum.notify import TransportTypeEnum
from core.schema.message.notify import WebPushDeliveryBatch

from notify.config.settings import settings
from notify.exc import WebPushClientInvalidException
from notify.schema.client import ClientTarget
from notify.schema.notification import NotificationContent
from notify.transport.base import DirectTransport, DeliveryDraft

logger = getLogger(__name__)

try:
    from webpush import WebPush, WebPushException, WebPushSubscription
except ImportError:  # pragma: no cover
    WebPush = None
    WebPushException = Exception
    WebPushSubscription = None

_OK_STATUSES = {200, 201, 202}
_DEAD_STATUSES = {404, 410}


class WebPushDeliveryError(Exception):
    """Raised by ``WebPushTransport.send``. ``dead`` marks an endpoint that no
    longer exists (HTTP 404/410) and must be deactivated."""

    def __init__(self, detail: str, *, dead: bool = False) -> None:
        super().__init__(detail)
        self.detail = detail
        self.dead = dead


class WebPushTransport(DirectTransport):
    """Direct Web Push via VAPID. Encryption (``webpush.WebPush.get``) is a cheap
    synchronous step; the actual HTTP delivery is awaited over a shared
    ``aiohttp`` session, so the worker can fan out with a real ``gather`` (no
    thread pool)."""

    type = TransportTypeEnum.webpush
    label = "Web Push"
    delivery_topic = NotifyDeliveryQueue.WEBPUSH

    def __init__(self) -> None:
        self._wp: WebPush | None = None
        self._wp_loaded = False

    def is_available(self) -> bool:
        return self._engine() is not None

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

    def application_server_key(self) -> str | None:
        """Base64url ``applicationServerKey`` derived from the VAPID public key,
        for ``PushManager.subscribe`` in the browser."""
        public = settings.vapid_public_key
        if not public:
            return None
        try:
            key = load_pem_public_key(public.encode())
            raw = key.public_bytes(
                Encoding.X962, PublicFormat.UncompressedPoint
            )
        except Exception:
            logger.warning("VAPID public key is not PEM; cannot derive key")
            return None
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    async def send(
        self,
        session: aiohttp.ClientSession,
        client: ClientTarget,
        content: NotificationContent,
    ) -> None:
        try:
            message = self._encrypt(client, content)
        except WebPushException as exc:
            raise WebPushDeliveryError(f"encrypt:{exc}", dead=False) from exc
        async with session.post(
            client.endpoint, data=message.encrypted, headers=message.headers
        ) as response:
            if response.status in _OK_STATUSES:
                return
            raise WebPushDeliveryError(
                f"http:{response.status}",
                dead=response.status in _DEAD_STATUSES,
            )

    def _encrypt(self, client: ClientTarget, content: NotificationContent):
        subscription = WebPushSubscription.model_validate(
            {
                "endpoint": client.endpoint,
                "keys": {
                    "p256dh": client.payload.get("p256dh"),
                    "auth": client.payload.get("auth"),
                },
            }
        )
        return self._engine().get(
            message=self._payload(content), subscription=subscription
        )

    @staticmethod
    def _payload(content: NotificationContent) -> dict:
        return {
            "title": content.title,
            "body": content.body,
            "url": content.action_url,
            "data": content.data,
        }

    def _engine(self) -> "WebPush | None":
        if not self._wp_loaded:
            self._wp = self._build_engine()
            self._wp_loaded = True
        return self._wp

    def _build_engine(self) -> "WebPush | None":
        if WebPush is None:
            return None
        private, public = settings.vapid_private_key, settings.vapid_public_key
        if not private or not public:
            return None
        try:
            return WebPush(
                private_key=private.encode(),
                public_key=public.encode(),
                subscriber=self._subscriber(),
            )
        except Exception:
            logger.exception("Failed to initialize WebPush from VAPID keys")
            return None

    @staticmethod
    def _subscriber() -> str | None:
        return (settings.WEB_PUSH_VAPID_SUBJECT or "").removeprefix(
            "mailto:"
        ) or None
