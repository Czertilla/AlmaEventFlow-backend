from profile.crypto import KeyRing, build_keyring, install_keyring
from profile.dependency._uow import profile_sessionmaker
from profile.uow.outbox import OutboxUOW
from profile.worker.outbox import NotificationOutboxPublisher

from fastapi import FastAPI
from faststream import FastStream

from core.app.contextmanager import AppContextManager


class ProfileContextManager(AppContextManager):
    def __init__(self) -> None:
        super().__init__()
        self.outbox_publisher = NotificationOutboxPublisher(
            OutboxUOW(profile_sessionmaker())
        )
        self.ring: KeyRing | None = None

    async def startup(self, app: FastAPI | FastStream) -> None:
        await super().startup(app)
        ring = build_keyring()
        await ring.self_test()
        install_keyring(ring)
        self.ring = ring
        self.outbox_publisher.start()

    async def shutdown(self, app: FastAPI | FastStream) -> None:
        await self.outbox_publisher.stop()
        if self.ring is not None:
            await self.ring.close()
            install_keyring(None)
            self.ring = None
        await super().shutdown(app)
