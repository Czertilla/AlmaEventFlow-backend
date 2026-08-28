from aiogram import Router

from core.utils.imports import load_common

router = Router(name="command/")
router.include_routers(*load_common(__name__, "router", Router))
