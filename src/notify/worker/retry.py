from notify.config.settings import settings
from notify.service.reenqueue import RetryReenqueueService
from notify.uow.outbox import RetryUOW
from notify.worker._base import PollingWorker


class RetryWorker(PollingWorker):
    """Periodically re-enqueues deliveries whose retry backoff has elapsed."""

    def __init__(self, uow: RetryUOW) -> None:
        super().__init__("notify-retry", settings.RETRY_POLL_INTERVAL_SECONDS)
        self._uow = uow

    async def work(self) -> int:
        return await RetryReenqueueService(self._uow).reenqueue_due()
