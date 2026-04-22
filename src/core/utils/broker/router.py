from typing import Iterable
from fastapi import FastAPI
from core.config.settings import settings
from faststream.broker.fastapi import StreamRouter
from faststream.broker.router import BrokerRouter


def include_mq_routers(
    app: FastAPI,
    stream_router: StreamRouter,
    routers: Iterable[BrokerRouter],
) -> None:
    if settings.MONOLITH:
        return
    for router in routers:
        stream_router.include_router(router)
    app.include_router(stream_router)
