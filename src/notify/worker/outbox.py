from core.broker.kafka import KafkaBroker

from notify.config.settings import settings
from notify.service.outbox import OutboxPublishService
from notify.uow.outbox import OutboxUOW
from notify.worker._base import PollingWorker


class OutboxPublisher(PollingWorker):
    """Periodically drains the transactional outbox into the delivery topics."""

    def __init__(self, uow: OutboxUOW, broker: KafkaBroker) -> None:
        super().__init__("notify-outbox", settings.OUTBOX_POLL_INTERVAL_SECONDS)
        self._uow = uow
        self._broker = broker

    async def work(self) -> int:
        return await OutboxPublishService(self._uow, self._broker).publish_batch()
