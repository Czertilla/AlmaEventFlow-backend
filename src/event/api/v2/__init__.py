from fastapi import APIRouter
from core.utils.imports import load_common

api_routers = load_common(__name__, "router", (APIRouter))

router = APIRouter(prefix="/v2")

for api_router in api_routers:
    router.include_router(api_router)
