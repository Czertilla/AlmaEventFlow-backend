from fastapi import APIRouter, FastAPI

from core.utils.imports import load_common
from core.broker.kafka import KafkaRouter, stream_router as kafka_root
from core.utils.broker.router import include_mq_routers

api_routers = load_common(__name__, "router", (APIRouter))
kafka_routers = load_common(__name__, "router", (KafkaRouter))

def include_routers(app: FastAPI):
    include_mq_routers(app, kafka_root, kafka_routers)
    for router in api_routers:
        app.include_router(router)
