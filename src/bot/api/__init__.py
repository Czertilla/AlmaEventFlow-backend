from fastapi import APIRouter, FastAPI

from bot.api.kafka import router as kafka_router
from core.broker.kafka import stream_router
from core.utils.broker.router import include_mq_routers
from core.utils.imports import load_common

api_routers = load_common(__name__, "router", (APIRouter))


def include_routers(app: FastAPI):
    include_mq_routers(app, stream_router, [kafka_router])
    service_router = APIRouter(prefix="/bot")
    for router in api_routers:
        service_router.include_router(router)
    app.include_router(service_router)
