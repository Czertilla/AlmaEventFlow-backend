from logging import getLogger
from fastapi import FastAPI
from core.app.contextmanager import AppContextManager

logger = getLogger()

class ProfileContextManager(AppContextManager):
    async def startup(self, app: FastAPI) -> None:
        """Initialize email-specific services"""
        await super().startup(app)


    async def shutdown(self, app: FastAPI) -> None:
        """Cleanup email-specific resources"""
        await super().shutdown(app)