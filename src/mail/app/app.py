from fastapi import FastAPI
from core.app import AppConfig
from mail.app.contextmanager import EmailContextManager
from mail.api.kafka import include_routers


app = FastAPI(
    **AppConfig(lifespan=EmailContextManager()).model_dump(),
)
include_routers(app)
