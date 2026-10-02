from fastapi import APIRouter, FastAPI

from core.broker.kafka import KafkaRouter
from core.broker.kafka import stream_router as kafka_root
from core.utils.broker.router import include_mq_routers
from core.utils.imports import load_common


def include_routers(app: FastAPI):
    api_routers = load_common(__name__, "router", (APIRouter))
    kafka_routers = load_common(__name__, "router", (KafkaRouter))
    include_mq_routers(app, kafka_root, kafka_routers)
    service_router = APIRouter(prefix="/org")
    for router in api_routers:
        service_router.include_router(router)
    app.include_router(service_router)
