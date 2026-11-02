from profile.service.outbox import NotificationOutboxService
from profile.uow.outbox import OutboxUOW

from core.config.settings import settings
from core.worker.polling import PollingWorker


class NotificationOutboxPublisher(PollingWorker):
    """Periodically hands the waiting notifications to `notify`."""

    def __init__(self, uow: OutboxUOW) -> None:
        super().__init__(
            "profile-outbox", settings.PROFILE_OUTBOX_POLL_INTERVAL_SECONDS
        )
        self._uow = uow

    async def work(self) -> int:
        return await NotificationOutboxService(self._uow).publish_batch()
