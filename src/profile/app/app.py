from profile.api import include_routers
from profile.app.contextmanager import ProfileContextManager

from fastapi import FastAPI

from core.app import AppConfig
from core.utils.cors import include_corse

app = FastAPI(
    **AppConfig(lifespan=ProfileContextManager()).model_dump(),
)
include_corse(app)
include_routers(app)
