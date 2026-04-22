from fastapi import FastAPI
from core.app import AppConfig
from core.utils.cors import include_corse
from geo.app.contextmanager import GeoContextManager
from geo.api import include_routers

app = FastAPI(
    **AppConfig(lifespan=GeoContextManager()).model_dump(),
)
include_corse(app)
include_routers(app)