from logging import getLogger
from fastapi import FastAPI
from core.app.contextmanager import AppContextManager


logger = getLogger()


class GeoContextManager(AppContextManager):
    async def startup(self, app: FastAPI) -> None:
        """Initialize geo-specific services"""
        await super().startup(app)
        # await init(documents)

    async def shutdown(self, app: FastAPI) -> None:
        """Cleanup geo-specific resources"""
        await super().shutdown(app)
