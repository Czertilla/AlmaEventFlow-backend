from fastapi import APIRouter, FastAPI

from core.utils.imports import load_common
from mail.api.kafka import include_routers as include_kafka_routers


def include_routers(app: FastAPI):
    include_kafka_routers(app)
    api_routers = load_common(__name__, "router", (APIRouter))
    service_router = APIRouter(prefix="/mail")
    for router in api_routers:
        service_router.include_router(router)
    app.include_router(service_router)
