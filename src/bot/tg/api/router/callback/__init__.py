from aiogram import Router

from core.utils.imports import load_common

router = Router(name="callback/")
router.include_routers(*load_common(__name__, "router", Router))
