from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from logging import getLogger
from profile.models.outbox import NotificationOutboxORM
from profile.uow.visibility import OutboxUOW
from uuid import UUID

from core.config.settings import settings
from core.enum.notify import NotificationCategory
from core.schema.message.notify import NotificationRequest
from core.service.base import BaseService, required_transaction
from core.utils.notify import send_notification

logger = getLogger(__name__)

MAX_DELAY = timedelta(hours=1)

Send = Callable[[NotificationRequest], Awaitable[None]]


class NotificationOutboxService(BaseService[OutboxUOW]):
    """Hands the notifications waiting in `notification_outbox` to `notify`.

    The row id is the `event_id` of the request, so a second hand-over of the same
    row (after a crash between the send and the commit) is a no-op for `notify`.
    Rows are locked with `FOR UPDATE SKIP LOCKED`.
    """

    def __init__(self, uow: OutboxUOW, send: Send = send_notification) -> None:
        super().__init__(uow)
        self._send = send

    async def publish_batch(self) -> int:
        async with self.uow as uow:
            published = await self._publish_batch(datetime.now(UTC))
            await uow.commit()
        return published

    @required_transaction
    async def _publish_batch(self, now: datetime) -> int:
        rows = await self.uow.notification_outbox.claim_due(
            settings.PROFILE_OUTBOX_BATCH_SIZE, now
        )
        published: list[UUID] = []
        for row in rows:
            try:
                await self._send(self._request(row))
            except Exception:
                logger.exception("Could not hand the notification %s to notify", row.id)
                await self._on_failure(row, now)
            else:
                published.append(row.id)
        await self.uow.notification_outbox.mark_published(published, now)
        return len(published)

    @required_transaction
    async def _on_failure(self, row: NotificationOutboxORM, now: datetime) -> None:
        attempts = row.attempts + 1
        if attempts >= settings.PROFILE_OUTBOX_MAX_ATTEMPTS:
            await self.uow.notification_outbox.mark_dead(row.id, attempts)
            return
        delay = min(
            timedelta(
                seconds=settings.PROFILE_OUTBOX_RETRY_BASE_SECONDS * 2**row.attempts
            ),
            MAX_DELAY,
        )
        await self.uow.notification_outbox.mark_retry(row.id, attempts, now + delay)

    @staticmethod
    def _request(row: NotificationOutboxORM) -> NotificationRequest:
        return NotificationRequest(
            event_id=row.id,
            person_ids=[row.person_id],
            category=NotificationCategory(row.category),
            title=row.title,
            body=row.body,
            data={key: str(value) for key, value in row.data.items()},
        )
