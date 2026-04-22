import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from logging import getLogger
from typing import Coroutine
from faststream import FastStream
from fastapi import FastAPI

logger = getLogger()


class AppContextManager:
    is_startup_completed: bool = False

    def __init__(self):
        self.background_tasks: list[Coroutine] = []

    async def startup(self, app: FastAPI | FastStream) -> None:
        """Initialize application services"""
        pass

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
