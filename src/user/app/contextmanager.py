from fastapi import FastAPI

from core.config.settings import Settings
from core.app.contextmanager import AppContextManager


settings = Settings()


class UserContextManager(AppContextManager):
    async def startup(self, app: FastAPI):
        await super().startup(app)

    async def shutdown(self, app: FastAPI):
        await super().shutdown(app)
