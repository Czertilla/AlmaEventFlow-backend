import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from logging import getLogger
from uuid import UUID

from core.enum.notify import DeliveryStatus, TransportTypeEnum
from core.schema.message.notify import WebPushDeliveryBatch
from core.service.base import BaseService, required_transaction

from notify.config.settings import settings
from notify.models.client import ClientORM
from notify.models.delivery import NotificationDeliveryORM
from notify.models.notification import NotificationORM
from notify.schema.client import ClientTarget
from notify.schema.notification import NotificationContent
from notify.service.batching import chunked
from notify.service.retry import policy
from notify.transport import registry
from notify.transport.webpush import WebPushDeliveryError, WebPushTransport
from notify.uow.delivery import WebPushDeliveryUOW

logger = getLogger(__name__)

Sendable = tuple[NotificationDeliveryORM, ClientORM]


class WebPushWorkerService(BaseService[WebPushDeliveryUOW]):
    """In-notify web push worker built for load: per page it loads all sendable
    deliveries with their endpoints in one query, fires all pushes in a single
    bounded ``gather`` (network only — the session is untouched during sends),
    then writes outcomes with grouped bulk updates. The parent notification is
    loaded once per batch, not per delivery."""

    async def handle(self, batch: WebPushDeliveryBatch) -> None:
        async with self.uow as uow:
            notification = await uow.notifications.get_by_id(
                batch.notification_id
            )
            if notification is None:
                await self._terminate(
                    batch.delivery_ids, DeliveryStatus.failed, "notification_missing"
                )
            elif self._expired(notification):
                await self._terminate(
                    batch.delivery_ids, DeliveryStatus.expired, "expired"
                )
            else:
                await self._dispatch(batch.delivery_ids, notification)
            await uow.commit()

    @required_transaction
    async def _terminate(
        self, delivery_ids, status: DeliveryStatus, reason: str
    ) -> None:
        await self.uow.deliveries.bulk_set_status(
            delivery_ids,
            status,
            last_error=reason,
            increment_attempts=False,
        )

    @required_transaction
    async def _dispatch(
        self, delivery_ids, notification: NotificationORM
    ) -> None:
        transport = registry.get(TransportTypeEnum.webpush)
        if not isinstance(transport, WebPushTransport) or not transport.is_available():
            await self.uow.deliveries.bulk_set_status(
                delivery_ids,
                DeliveryStatus.retry_scheduled,
                next_attempt_at=self._flat_retry_at(),
                last_error="transport_unavailable",
            )
            return
        content = NotificationContent.from_model(notification)
        for page in chunked(list(delivery_ids), settings.WEBPUSH_LOAD_PAGE_SIZE):
            await self._process_page(transport, list(page), content)
            await self.uow.commit()

    @required_transaction
    async def _process_page(
        self,
        transport: WebPushTransport,
        page_ids: list[UUID],
        content: NotificationContent,
    ) -> None:
        rows = await self.uow.deliveries.load_sendable(page_ids)
        if not rows:
            return
        sendable, skipped = self._split(rows)
        results = (
            await self._send_all(transport, sendable, content)
            if sendable
            else []
        )
        await self._persist(sendable, results, skipped)

    @staticmethod
    def _split(
        rows: list[tuple[NotificationDeliveryORM, ClientORM | None]],
    ) -> tuple[list[Sendable], list[UUID]]:
        sendable: list[Sendable] = []
        skipped: list[UUID] = []
        for delivery, client in rows:
            if client is None or not client.is_active:
                skipped.append(delivery.id)
            else:
                sendable.append((delivery, client))
        return sendable, skipped

    async def _send_all(
        self,
        transport: WebPushTransport,
        sendable: list[Sendable],
        content: NotificationContent,
    ) -> list[WebPushDeliveryError | None]:
        semaphore = asyncio.Semaphore(settings.WEBPUSH_SEND_CONCURRENCY)

        async def _send(client: ClientORM) -> WebPushDeliveryError | None:
            async with semaphore:
                try:
                    await transport.push(
                        ClientTarget.model_validate(client), content
                    )
                    return None
                except WebPushDeliveryError as exc:
                    return exc
                except Exception as exc:
                    logger.exception("Unexpected web push send error")
                    return WebPushDeliveryError(str(exc), dead=False)

        return await asyncio.gather(
            *(_send(client) for _, client in sendable)
        )

    @required_transaction
    async def _persist(
        self,
        sendable: list[Sendable],
        results: list[WebPushDeliveryError | None],
        skipped: list[UUID],
    ) -> None:
        sent: list[UUID] = []
        failed: list[UUID] = []
        dead_clients: list[UUID] = []
        dead_deliveries: list[UUID] = []
        retries: dict[datetime, list[UUID]] = defaultdict(list)
        for (delivery, client), outcome in zip(sendable, results):
            if outcome is None:
                sent.append(delivery.id)
            elif outcome.dead:
                dead_clients.append(client.id)
                dead_deliveries.append(delivery.id)
            else:
                self._schedule_retry(delivery, failed, retries)

        deliveries = self.uow.deliveries
        await deliveries.bulk_set_status(sent, DeliveryStatus.sent)
        await deliveries.bulk_set_status(
            skipped,
            DeliveryStatus.skipped,
            last_error="endpoint_inactive",
            increment_attempts=False,
        )
        await deliveries.bulk_set_status(
            failed, DeliveryStatus.failed, last_error="webpush_failed"
        )
        if dead_deliveries:
            await self.uow.clients.deactivate(dead_clients)
            await deliveries.bulk_set_status(
                dead_deliveries, DeliveryStatus.failed, last_error="endpoint_gone"
            )
        for next_attempt_at, ids in retries.items():
            await deliveries.bulk_set_status(
                ids,
                DeliveryStatus.retry_scheduled,
                next_attempt_at=next_attempt_at,
            )

    @staticmethod
    def _schedule_retry(
        delivery: NotificationDeliveryORM,
        failed: list[UUID],
        retries: dict[datetime, list[UUID]],
    ) -> None:
        decision = policy.after_failure(
            delivery.attempts + 1, delivery.max_attempts
        )
        if decision.status is DeliveryStatus.failed:
            failed.append(delivery.id)
        else:
            retries[decision.next_attempt_at].append(delivery.id)

    @staticmethod
    def _flat_retry_at() -> datetime:
        return datetime.now(timezone.utc) + timedelta(
            seconds=settings.DELIVERY_RETRY_BACKOFF_BASE_SECONDS
        )

    @staticmethod
    def _expired(notification: NotificationORM) -> bool:
        return (
            notification.expires_at is not None
            and notification.expires_at < datetime.now(timezone.utc)
        )
