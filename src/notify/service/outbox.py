from logging import getLogger

from core.broker.kafka import KafkaBroker
from core.enum.mq import dlq_for
from core.service.base import BaseService, required_transaction

from notify.config.settings import settings
from notify.models.outbox import OutboxEventORM
from notify.uow.outbox import OutboxUOW

logger = getLogger(__name__)


class OutboxPublishService(BaseService[OutboxUOW]):
    """Drains pending outbox rows and publishes them to their delivery topics.

    Rows are locked with ``FOR UPDATE SKIP LOCKED`` so several publisher
    instances never publish the same row twice."""

    def __init__(self, uow: OutboxUOW, broker: KafkaBroker) -> None:
        super().__init__(uow)
        self.broker = broker

    async def publish_batch(self) -> int:
        async with self.uow as uow:
            published = await self._publish_batch()
            await uow.commit()
        return published

    @required_transaction
    async def _publish_batch(self) -> int:
        rows = await self.uow.outbox.claim_pending(settings.OUTBOX_BATCH_SIZE)
        if not rows:
            return 0
        published: list[int] = []
        for row in rows:
            try:
                await self.broker.publish(row.payload, row.topic)
            except Exception:
                logger.exception("Outbox publish failed for row %s", row.id)
                await self._on_failure(row)
                continue
            published.append(row.id)
        await self.uow.outbox.mark_published(published)
        return len(published)

    @required_transaction
    async def _on_failure(self, row: OutboxEventORM) -> None:
        if row.attempts + 1 < settings.OUTBOX_MAX_ATTEMPTS:
            await self.uow.outbox.mark_failed(row.id)
            return
        await self.uow.outbox.mark_dead(row.id)
        try:
            await self.broker.publish(row.payload, dlq_for(row.topic))
        except Exception:
            logger.exception("Outbox dead-letter publish failed for %s", row.id)
