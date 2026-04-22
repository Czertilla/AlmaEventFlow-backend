from logging import getLogger
from fastapi import FastAPI
from core.app.contextmanager import AppContextManager

logger = getLogger()


class OrgContextManager(AppContextManager):
    async def startup(self, app: FastAPI) -> None:
        """Initialize org-specific services"""
        await super().startup(app)

    async def shutdown(self, app: FastAPI) -> None:
        """Cleanup org-specific resources"""
        await super().shutdown(app)
