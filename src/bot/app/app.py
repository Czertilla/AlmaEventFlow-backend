from fastapi import FastAPI

from bot.api import include_routers
from bot.app.contextmanager import BotContextManager
from core.app import AppConfig

app = FastAPI(
    **AppConfig(
        lifespan=BotContextManager()
    ).model_dump(),
)
include_routers(app)
