import asyncio
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from logging import getLogger

from fastapi import FastAPI
from faststream import FastStream

from core.config.settings import settings

logger = getLogger(__name__)


def _broker_summary() -> str:
    if settings.IN_MEMORY_BROKER:
        return "in-memory"
    return (
        f"kafka {settings.KAFKA_HOST}:{settings.KAFKA_PORT} "
        f"security={settings.KAFKA_SECURITY_PROTOCOL or 'plaintext'} "
        f"group={settings.KAFKA_CONSUMER_GROUP or '-'}"
    )


class AppContextManager:
    is_startup_completed: bool = False

    def __init__(self):
        self.background_tasks: list[Coroutine] = []

    async def startup(self, app: FastAPI | FastStream) -> None:
        """Initialize application services"""
        if not getLogger().handlers:
            # lazy: importing the package swaps the global logger class
            from core.config.logger import setup

            setup()
            logger.info("Logging configured: the process had no log config")
        logger.info(
            "Starting %s: monolith=%s, broker=%s",
            type(self).__name__,
            settings.MONOLITH,
            _broker_summary(),
        )
        if settings.IN_MEMORY_BROKER and not settings.MONOLITH:
            logger.warning(
                "IN_MEMORY_BROKER is on outside the monolith: messages "
                "published here never reach other services"
            )

    async def shutdown(self, app: FastAPI | FastStream) -> None:
        if self.background_tasks:
            asyncio.wait([self.background_tasks][::-1])

    @asynccontextmanager
    async def __call__(self, app: FastAPI | FastStream) -> AsyncIterator[None]:
        """Application lifespan context manager"""
        await self.startup(app)
        try:
            yield
        finally:
            await self.shutdown(app)
