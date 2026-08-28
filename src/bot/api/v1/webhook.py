from fastapi import APIRouter

from bot.tg.api.webhook import router as tg_router

router = APIRouter(prefix="/webhook")

router.include_router(tg_router, prefix="/tg")