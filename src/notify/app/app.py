from fastapi import FastAPI

from core.app import AppConfig
from core.utils.cors import include_corse
from notify.api import include_routers
from notify.app.contextmanager import NotifyContextManager

app = FastAPI(
    **AppConfig(lifespan=NotifyContextManager()).model_dump(),
)
include_corse(app)
include_routers(app)
