from logging import getLogger
from profile.app.contextmanager import ProfileContextManager

from fastapi import FastAPI
from faststream import FastStream

from core.app.contextmanager import AppContextManager
from notify.app.contextmanager import NotifyContextManager

logger = getLogger()


class AEFContextManager(AppContextManager):
    """Modular-monolith lifespan. Aggregates the per-service lifecycles that
    own background work; without this the notify outbox publisher and retry
    worker and the profile notification publisher never start in the combined
    process."""

    def __init__(self) -> None:
        super().__init__()
        self.notify = NotifyContextManager()
        self.profile = ProfileContextManager()

    async def startup(self, app: FastAPI | FastStream) -> None:
        await super().startup(app)
        await self.notify.startup(app)
        await self.profile.startup(app)

    async def shutdown(self, app: FastAPI | FastStream) -> None:
        await self.profile.shutdown(app)
        await self.notify.shutdown(app)
        await super().shutdown(app)
