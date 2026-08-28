from fastapi import FastAPI

from aef.api import include_routers
from aef.app.contextmanager import AEFContextManager
from core.app import AppConfig
from core.utils.cors import include_corse

app = FastAPI(
    **AppConfig(lifespan=AEFContextManager()).model_dump(),
)
include_corse(app)
include_routers(app)
