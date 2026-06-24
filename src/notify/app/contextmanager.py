from logging import getLogger
from fastapi import FastAPI
from core.app.contextmanager import AppContextManager
from core.broker.kafka import broker

from notify.dependency._uow import notify_sessionmaker
from notify.uow.outbox import OutboxUOW, RetryUOW
from notify.worker.outbox import OutboxPublisher
from notify.worker.retry import RetryWorker

logger = getLogger()


class NotifyContextManager(AppContextManager):
    def __init__(self) -> None:
        super().__init__()
        self.outbox_publisher = OutboxPublisher(
            OutboxUOW(notify_sessionmaker()), broker
        )
        self.retry_worker = RetryWorker(RetryUOW(notify_sessionmaker()))

    async def startup(self, app: FastAPI) -> None:
        """Start notify background workers (outbox publisher, retry worker)."""
        await super().startup(app)
        self.outbox_publisher.start()
        self.retry_worker.start()

    async def shutdown(self, app: FastAPI) -> None:
        """Stop notify background workers."""
        await self.retry_worker.stop()
        await self.outbox_publisher.stop()
        await super().shutdown(app)
