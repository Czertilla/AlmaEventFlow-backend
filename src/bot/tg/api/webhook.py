from aiogram.types import Update, WebhookInfo
from fastapi import APIRouter, HTTPException
from fastapi.requests import Request

from bot.tg.dependency import BotDep, DpDep
from core.config.settings import settings

router = APIRouter(tags=["tg"])

SECRET_TOKEN_HEADER = "x-telegram-bot-api-secret-token"


@router.post("")
async def webhook(request: Request, bot: BotDep, dp: DpDep) -> None:
    """
    Handles incoming Telegram updates via webhook.

    Validates the ``X-Telegram-Bot-Api-Secret-Token`` header (when
    ``BOT_TG_WEBHOOK_SECRET`` is configured) so third parties can't inject
    fake updates, then validates the request JSON as an aiogram Update model
    and feeds it to the aiogram Dispatcher.

    Args:
        request: The FastAPI Request object containing the update data.
        bot: The Telegram bot instance.
        dp: The aiogram dispatcher instance.
    """
    if settings.BOT_TG_WEBHOOK_SECRET is not None:
        expected = settings.BOT_TG_WEBHOOK_SECRET.get_secret_value()
        if request.headers.get(SECRET_TOKEN_HEADER) != expected:
            raise HTTPException(status_code=403, detail="Invalid secret token")
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)


@router.get("")
async def webhook_info(bot: BotDep) -> WebhookInfo:
    """
    Returns information about the webhook.

    Args:
        bot: The Telegram bot instance.

    Returns:
        WebhookInfo: Information about the current webhook.
    """
    return await bot.get_webhook_info()
