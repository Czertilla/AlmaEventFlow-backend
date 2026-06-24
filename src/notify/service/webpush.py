from datetime import datetime, timezone
from logging import getLogger
from uuid import UUID

from core.enum.notify import DeliveryStatus, TransportTypeEnum
from core.schema.message.notify import WebPushDeliveryBatch
from core.service.base import BaseService, required_transaction

from notify.models.delivery import NotificationDeliveryORM
from notify.models.notification import NotificationORM
from notify.schema.client import ClientTarget
from notify.schema.notification import NotificationContent
from notify.service.retry import policy
from notify.transport import registry
from notify.transport.webpush import WebPushDeliveryError, WebPushTransport
from notify.uow.delivery import WebPushDeliveryUOW

logger = getLogger(__name__)


class WebPushWorkerService(BaseService[WebPushDeliveryUOW]):
    """In-notify web push worker. Consumes a (typically single-item) web push
    batch, loads each delivery from the shared database, sends the push and
    writes the per-delivery outcome directly. Deliveries already in a terminal
    status are skipped, so redelivered batches never re-send."""

    async def handle(self, batch: WebPushDeliveryBatch) -> None:
        async with self.uow as uow:
            for delivery_id in batch.delivery_ids:
                await self._handle_one(delivery_id)
            await uow.commit()

    @required_transaction
    async def _handle_one(self, delivery_id: UUID) -> None:
        delivery = await self.uow.deliveries.get_by_id(delivery_id)
        if delivery is None:
            logger.warning("Web push for unknown delivery %s", delivery_id)
            return
        if delivery.status in DeliveryStatus.terminal():
            return
        notification = await self.uow.notifications.get_by_id(
            delivery.notification_id
        )
        if notification is None:
            await self._set(delivery, DeliveryStatus.failed, "notification_missing")
            return
        if self._expired(notification):
            await self._set(delivery, DeliveryStatus.expired, "expired")
            return
        await self._deliver(delivery, notification)

    @required_transaction
    async def _deliver(
        self,
        delivery: NotificationDeliveryORM,
        notification: NotificationORM,
    ) -> None:
        client = (
            await self.uow.clients.get_by_id(delivery.client_id)
            if delivery.client_id is not None
            else None
        )
        if client is None or not client.is_active:
            await self._set(delivery, DeliveryStatus.skipped, "endpoint_inactive")
            return
        transport = registry.get(TransportTypeEnum.webpush)
        if not isinstance(transport, WebPushTransport):
            await self._set(delivery, DeliveryStatus.retry_scheduled, "transport_unavailable")
            return
        try:
            await transport.push(
                ClientTarget.model_validate(client),
                NotificationContent.from_model(notification),
            )
        except WebPushDeliveryError as exc:
            await self._on_error(delivery, client.id, exc)
            return
        await self._set(delivery, DeliveryStatus.sent, None)

    @required_transaction
    async def _on_error(
        self,
        delivery: NotificationDeliveryORM,
        client_id: UUID,
        exc: WebPushDeliveryError,
    ) -> None:
        if exc.dead:
            await self.uow.clients.deactivate([client_id])
            await self._set(delivery, DeliveryStatus.failed, exc.detail)
            return
        decision = policy.after_failure(
            delivery.attempts + 1, delivery.max_attempts
        )
        await self._set(
            delivery, decision.status, exc.detail, decision.next_attempt_at
        )

    @required_transaction
    async def _set(
        self,
        delivery: NotificationDeliveryORM,
        status: DeliveryStatus,
        error: str | None,
        next_attempt_at: datetime | None = None,
    ) -> None:
        await self.uow.deliveries.update_one(
            delivery.id,
            {
                "status": status,
                "attempts": delivery.attempts + 1,
                "last_error": error,
                "next_attempt_at": next_attempt_at,
            },
        )

    @staticmethod
    def _expired(notification: NotificationORM) -> bool:
        return (
            notification.expires_at is not None
            and notification.expires_at < datetime.now(timezone.utc)
        )
