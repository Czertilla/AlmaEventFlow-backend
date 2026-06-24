from collections import defaultdict
from logging import getLogger
from uuid import UUID

from core.service.base import BaseService, required_transaction

from notify.config.settings import settings
from notify.models.delivery import NotificationDeliveryORM
from notify.models.notification import NotificationORM
from notify.schema.account import AccountRead
from notify.schema.notification import NotificationContent
from notify.service.batching import build_outbox_rows
from notify.transport import registry
from notify.transport.base import DeliveryDraft, DeliveryTarget, PlanContext
from notify.uow.outbox import RetryUOW

logger = getLogger(__name__)


class RetryReenqueueService(BaseService[RetryUOW]):
    """Rebuilds transport batches for deliveries whose backoff has elapsed and
    re-enqueues them through the outbox, then resets them to ``pending``. Only
    deliveries that still need retry are collected, so each retry batch is
    minimal. Email deliveries whose address can no longer be resolved fail
    terminally instead of being retried forever."""

    async def reenqueue_due(self) -> int:
        async with self.uow as uow:
            count = await self._reenqueue_due()
            if count:
                await uow.commit()
        return count

    @required_transaction
    async def _reenqueue_due(self) -> int:
        due = await self.uow.deliveries.get_due_retries(settings.OUTBOX_BATCH_SIZE)
        if not due:
            return 0
        by_notification: dict[UUID, list[NotificationDeliveryORM]] = defaultdict(
            list
        )
        for delivery in due:
            by_notification[delivery.notification_id].append(delivery)
        requeued = 0
        for notification_id, deliveries in by_notification.items():
            requeued += await self._reenqueue_notification(
                notification_id, deliveries
            )
        return requeued

    @required_transaction
    async def _reenqueue_notification(
        self,
        notification_id: UUID,
        deliveries: list[NotificationDeliveryORM],
    ) -> int:
        notification = await self.uow.notifications.get_by_id(notification_id)
        if notification is None:
            logger.warning(
                "Notification %s gone, failing %d retry deliveries",
                notification_id,
                len(deliveries),
            )
            await self.uow.deliveries.mark_failed(
                [d.id for d in deliveries], "notification_missing"
            )
            return 0
        content = NotificationContent.from_model(notification)
        drafts: dict = defaultdict(list)
        ready: list[UUID] = []
        unresolved: list[UUID] = []
        accounts: dict[UUID, AccountRead | None] = {}
        for delivery in deliveries:
            draft = await self._draft(
                delivery, notification, content, accounts
            )
            if draft is None:
                unresolved.append(delivery.id)
                continue
            drafts[delivery.transport].append(draft)
            ready.append(delivery.id)
        if unresolved:
            logger.warning(
                "Failing %d retry deliveries with unresolved address",
                len(unresolved),
            )
            await self.uow.deliveries.mark_failed(unresolved, "address_unresolved")
        for row in build_outbox_rows(notification_id, drafts):
            await self.uow.outbox.add_one(
                {"topic": row.topic, "payload": row.payload}
            )
        await self.uow.deliveries.mark_pending(ready)
        return len(ready)

    async def _draft(
        self,
        delivery: NotificationDeliveryORM,
        notification: NotificationORM,
        content: NotificationContent,
        accounts: dict[UUID, AccountRead | None],
    ) -> DeliveryDraft | None:
        transport = registry.get(delivery.transport)
        if transport is None:
            return None
        account = None
        if not transport.requires_client:
            account = await self._account(delivery.user_id, accounts)
            if account is None or not account.email:
                return None
        ctx = PlanContext(
            notification_id=notification.id,
            user_id=delivery.user_id,
            content=content,
            account=account,
            expires_at=notification.expires_at,
        )
        return DeliveryDraft(
            delivery_id=delivery.id, ctx=ctx, target=DeliveryTarget()
        )

    async def _account(
        self, user_id: UUID, cache: dict[UUID, AccountRead | None]
    ) -> AccountRead | None:
        if user_id not in cache:
            row = await self.uow.accounts.get_by_id(user_id)
            cache[user_id] = (
                AccountRead.model_validate(row) if row is not None else None
            )
        return cache[user_id]
