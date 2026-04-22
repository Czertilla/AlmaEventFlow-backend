from logging import getLogger
from fastapi import FastAPI
from core.app.contextmanager import AppContextManager

logger = getLogger()


class EventContextManager(AppContextManager):
    async def startup(self, app: FastAPI) -> None:
        """Initialize event-specific services"""
        await super().startup(app)

    async def shutdown(self, app: FastAPI) -> None:
        """Cleanup event-specific resources"""
        await super().shutdown(app)