from fastapi import FastAPI
from core.app import AppConfig
from core.utils.cors import include_corse
from org.app.contextmanager import OrgContextManager
from org.api import include_routers

app = FastAPI(
    **AppConfig(lifespan=OrgContextManager()).model_dump(),
)
include_corse(app)
include_routers(app)