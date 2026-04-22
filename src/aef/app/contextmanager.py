from logging import getLogger
from fastapi import FastAPI
from core.app.contextmanager import AppContextManager

logger = getLogger()


class AEFContextManager(AppContextManager):
    async def startup(self, app: FastAPI) -> None:
        await super().startup(app)

    async def shutdown(self, app: FastAPI) -> None:
        await super().shutdown(app)