from typing import Any, Iterable
from fastapi import APIRouter, FastAPI
from core.config.settings import settings


def include_mq_routers(
    app: FastAPI,
    stream_router: APIRouter,
    routers: Iterable[Any],
) -> None:
    if settings.IN_MEMORY_BROKER:
        return
    for router in routers:
        stream_router.include_router(router)
    app.include_router(stream_router)
