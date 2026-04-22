from fastapi import FastAPI
from core.app import AppConfig
from core.utils.cors import include_corse
from aef.app.contextmanager import AEFContextManager
from aef.api import include_routers


app = FastAPI(
    **AppConfig(lifespan=AEFContextManager()).model_dump(),
)
include_corse(app)
include_routers(app)
