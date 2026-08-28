from logging import getLogger

from fastapi import FastAPI

from bot.tg.app.contextmanager import TGBotContextManager
from bot.tg.dependency.bot import bot as _bot
from bot.tg.dependency.dp import dp as _dp
from core.app.contextmanager import AppContextManager
from notify.app.contextmanager import NotifyContextManager

logger = getLogger()


class AEFContextManager(TGBotContextManager, AppContextManager):
    """Modular-monolith lifespan. Aggregates the per-service lifecycles that
    own background work; without this the notify outbox publisher and retry
    worker never start in the combined process."""

    def __init__(self) -> None:
        super().__init__(bot=_bot, dp=_dp)
        self.notify = NotifyContextManager()

    async def startup(self, app: FastAPI) -> None:
        await super().startup(app)
        await self.notify.startup(app)

    async def shutdown(self, app: FastAPI) -> None:
        await self.notify.shutdown(app)
        await super().shutdown(app)
