from asyncio import create_task
from logging import getLogger

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ChatAdministratorRights
from aiogram3_di import setup_di
from fastapi import FastAPI

from bot.tg.api.router import register_routers
from bot.tg.service.commands import CommandMenuService
from bot.tg.text.description import get_bot_profile_texts
from core.app.contextmanager import AppContextManager
from core.config.settings import settings
from core.enum.config import TgBotFeedType

logger = getLogger(__name__)

GROUP_ADMIN_RIGHTS = ChatAdministratorRights(
    is_anonymous=False,
    can_manage_chat=False,
    can_delete_messages=False,
    can_manage_video_chats=False,
    can_restrict_members=False,
    can_promote_members=False,
    can_change_info=False,
    can_invite_users=False,
    can_post_stories=False,
    can_edit_stories=False,
    can_delete_stories=False,
    can_send_welcome_messages=False,
    can_pin_messages=True,
)


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
        register_routers(self.dp)

    def setup_di(self):
        setup_di(self.dp)

    async def set_commands(self):
        if self.bot is None:
            return
        menu = CommandMenuService(self.bot)
        await menu.setup_static()
        try:
            await menu.refresh_superusers()
        except Exception:
            logger.exception("could not refresh superuser command menus")

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

    async def set_profile(self):
        if self.bot is None:
            return
        try:
            for text in get_bot_profile_texts():
                await self.bot.set_my_description(
                    text.description, text.language_code
                )
                await self.bot.set_my_short_description(
                    text.short_description, text.language_code
                )
            await self.bot.set_my_default_administrator_rights(
                GROUP_ADMIN_RIGHTS, for_channels=False
            )
        except TelegramAPIError:
            logger.exception("could not update the bot profile")

    async def start_polling(self):
        await self.bot.delete_webhook()
        create_task(self.dp.start_polling(self.bot))

    async def stop_polling(self):
        await self.dp.stop_polling()

    async def check_identity(self):
        if self.bot is None:
            return
        try:
            me = await self.bot.get_me()
        except Exception:
            logger.exception(
                "Telegram getMe failed: the bot token is invalid or "
                "api.telegram.org is unreachable, nothing can be delivered"
            )
            return
        logger.info(
            "Telegram bot authorised: @%s (id=%s), feed=%s",
            me.username,
            me.id,
            settings.BOT_TG_FEED_TYPE,
        )

    async def startup(self, app: FastAPI):
        await super().startup(app)
        await self.check_identity()
        self.register_handlers()
        self.setup_di()
        await self.set_commands()
        await self.set_profile()
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
