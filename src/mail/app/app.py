from fastapi import FastAPI

from core.app import AppConfig
from mail.api import include_routers

app = FastAPI(
    **AppConfig().model_dump(),
)
include_routers(app)
