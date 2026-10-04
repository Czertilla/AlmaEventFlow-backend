from fastapi import APIRouter

from core.broker.kafka import stream_router
from core.utils.broker.router import include_mq_routers

PREFIX = "/user"


def include_routers(app: APIRouter):
    from user.api.kafka.sub.person import router as person_router
    from user.api.kafka.sub.telegram import router as telegram_rpc_router
    from user.api.v1 import include_routers as include_v1_routers

    include_mq_routers(app, stream_router, [person_router, telegram_rpc_router])
    include_v1_routers(app, PREFIX)
