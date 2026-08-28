from asyncio import create_task
from logging import getLogger

from aiogram import Bot, Dispatcher
from aiogram.client.telegram import TEST
from aiogram3_di import setup_di
from fastapi import FastAPI

from bot.tg.api.router import register_routers
from bot.tg.text.commands import get_commands_hints
from bot.tg.text.description import get_bot_descriptions
from core.app.contextmanager import AppContextManager
from core.config.settings import settings
from core.enum.config import TgBotFeedType

logger = getLogger(__name__)


class TGBotContextManager(AppContextManager):
    def __init__(
        self,
        *,
        bot: Bot | None = None,
        dp: Dispatcher | None = None,
    ):
        super().__init__()
        self.bot = bot
        self.dp = dp

    def register_handlers(self):
        # self.dp.pre_checkout_query.register(pre_checkout_handler)
        register_routers(self.dp)

    def setup_di(self):
        setup_di(self.dp)

    async def set_commands(self):
        for arg in await get_commands_hints():
            if await self.bot.set_my_commands(**arg):
                logger.info(
                    f"Success setup bot commands for scope={arg['scope']} "
                    f"and locale={arg['language_code']}"
                )
            else:
                logger.error(
                    f"Failed setup bot commands for scope={arg['scope']} "
                    f"and locale={arg['language_code']}"
                )

    async def set_webhook(self):
        url = f"https://{settings.APP_HOST}{settings.BOT_TG_WEBHOOK}"
        logger.info(f"Setting up webhook on {url}")
        secret = (
            settings.BOT_TG_WEBHOOK_SECRET.get_secret_value()
            if settings.BOT_TG_WEBHOOK_SECRET
            else None
        )
        await self.bot.set_webhook(
            url=url,
            allowed_updates=self.dp.resolve_used_update_types(),
            drop_pending_updates=True,
            secret_token=secret,
        )

    async def set_description(self):
        for description, locale in get_bot_descriptions():
            await self.bot.set_my_description(description, locale)

    async def start_polling(self):
        await self.bot.delete_webhook()
        create_task(self.dp.start_polling(self.bot))

    async def stop_polling(self):
        await self.dp.stop_polling()

    async def startup(self, app: FastAPI):
        await super().startup(app)
        self.register_handlers()
        self.setup_di()
        await self.set_commands()
        await self.set_description()
        if (feed_type := settings.BOT_TG_FEED_TYPE) == TgBotFeedType.WEBHOOK:
            await self.set_webhook()
        elif feed_type == TgBotFeedType.POLLING:
            await self.start_polling()

    async def shutdown(self, app: FastAPI):
        await super().shutdown(app)
        if (feed_type := settings.BOT_TG_FEED_TYPE) == TgBotFeedType.WEBHOOK:
            await self.bot.delete_webhook()
        elif feed_type == TgBotFeedType.POLLING:
            await self.stop_polling()
