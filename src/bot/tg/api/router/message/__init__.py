from aiogram import Router

from core.utils.imports import load_common

router = Router(name="message/")
message_routers = load_common(__name__, "router", Router)
message_routers and router.include_routers(*message_routers)
