from fastapi import FastAPI
from core.app import AppConfig

from core.utils.cors import include_corse
from user.app.contextmanager import UserContextManager
from user.api import include_routers

app = FastAPI(
    **AppConfig(lifespan=UserContextManager()).model_dump(),
)
include_corse(app)
include_routers(app)
