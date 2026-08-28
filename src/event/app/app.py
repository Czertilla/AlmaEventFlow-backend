from fastapi import FastAPI

from core.app import AppConfig
from core.utils.cors import include_corse
from event.api import include_routers
from event.app.contextmanager import EventContextManager

app = FastAPI(
    **AppConfig(lifespan=EventContextManager()).model_dump(),
)
include_corse(app)
include_routers(app)
