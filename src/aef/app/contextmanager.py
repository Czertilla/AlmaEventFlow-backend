from logging import getLogger
from fastapi import FastAPI
from core.app.contextmanager import AppContextManager

from notify.app.contextmanager import NotifyContextManager

logger = getLogger()


class AEFContextManager(AppContextManager):
    """Modular-monolith lifespan. Aggregates the per-service lifecycles that
    own background work; without this the notify outbox publisher and retry
    worker never start in the combined process."""

    def __init__(self) -> None:
        super().__init__()
        self.notify = NotifyContextManager()

    async def startup(self, app: FastAPI) -> None:
        await super().startup(app)
        await self.notify.startup(app)

    async def shutdown(self, app: FastAPI) -> None:
        await self.notify.shutdown(app)
        await super().shutdown(app)
