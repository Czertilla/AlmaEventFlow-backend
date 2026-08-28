from fastapi import FastAPI

from core.app import AppConfig
from mail.api.kafka import include_routers
from mail.app.contextmanager import EmailContextManager

app = FastAPI(
    **AppConfig(lifespan=EmailContextManager()).model_dump(),
)
include_routers(app)
