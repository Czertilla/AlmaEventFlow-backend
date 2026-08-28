from logging import getLogger

from bot.tg.app.contextmanager import TGBotContextManager
from bot.tg.dependency.bot import bot as _bot
from bot.tg.dependency.dp import dp as _dp
from core.app.contextmanager import AppContextManager

logger = getLogger(__name__)


class BotContextManager(TGBotContextManager, AppContextManager):
    def __init__(self):
        super().__init__(bot=_bot, dp=_dp)

    async def startup(self, app):
        return await super().startup(app)

    async def shutdown(self, app):
        return await super().shutdown(app)
