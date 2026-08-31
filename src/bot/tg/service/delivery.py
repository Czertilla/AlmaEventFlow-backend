from datetime import datetime, timezone
from logging import getLogger

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyParameters,
)

from bot.tg.uow.message import TelegramMessageUOW
from core.enum.notify import DeliveryStatus
from core.schema.message.notify import DeliveryResult, TelegramDeliveryItem
from core.service.base import BaseService

logger = getLogger(__name__)

UPDATED_PING_TEXT = "🔄 Обновлено"


class TelegramDeliveryService(BaseService[TelegramMessageUOW]):
    """Sends (or, for a domain id already delivered to this chat, edits) one
    Telegram delivery. Edits are silent on Telegram — a real notification
    still needs the reply ping — so an edit is always paired with a small
    reply to the original message."""

    def __init__(self, uow: TelegramMessageUOW, bot: Bot) -> None:
        super().__init__(uow)
        self.bot = bot

    async def deliver(self, item: TelegramDeliveryItem) -> DeliveryResult:
        if self._is_expired(item):
            return DeliveryResult(
                delivery_id=item.delivery_id,
                status=DeliveryStatus.expired,
                error="expired",
            )
        chat_id = int(item.chat_id)
        markup = self._markup(item)
        existing = await self._existing_message(item, chat_id)
        try:
            message_id = await self._send_or_edit(
                item, chat_id, markup, existing
            )
        except TelegramForbiddenError as exc:
            logger.info("Telegram forbidden for chat %s: %s", chat_id, exc)
            return DeliveryResult(
                delivery_id=item.delivery_id,
                status=DeliveryStatus.failed,
                error="forbidden",
            )
        except TelegramBadRequest as exc:
            if existing is not None and "message is not modified" in str(
                exc
            ).lower():
                # Redelivered batch with unchanged content — not an error.
                return DeliveryResult(
                    delivery_id=item.delivery_id,
                    status=DeliveryStatus.sent,
                    provider_message_id=str(existing.message_id),
                )
            logger.warning(
                "Telegram bad request for chat %s: %s", chat_id, exc
            )
            return DeliveryResult(
                delivery_id=item.delivery_id,
                status=DeliveryStatus.failed,
                error=str(exc),
            )
        except Exception as exc:
            logger.exception("Telegram send failed for chat %s", chat_id)
            return DeliveryResult(
                delivery_id=item.delivery_id,
                status=DeliveryStatus.retry_scheduled,
                error=str(exc),
            )
        return DeliveryResult(
            delivery_id=item.delivery_id,
            status=DeliveryStatus.sent,
            provider_message_id=str(message_id),
        )

    async def _existing_message(self, item: TelegramDeliveryItem, chat_id: int):
        if not item.correlation_key:
            return None
        async with self.uow as uow:
            return await uow.messages.get(item.correlation_key, chat_id)

    async def _send_or_edit(
        self, item: TelegramDeliveryItem, chat_id: int, markup, existing
    ) -> int:
        if existing is not None:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=existing.message_id,
                text=item.text,
                reply_markup=markup,
                parse_mode="HTML",
            )
            await self.bot.send_message(
                chat_id=chat_id,
                text=UPDATED_PING_TEXT,
                reply_parameters=ReplyParameters(
                    message_id=existing.message_id,
                    allow_sending_without_reply=True,
                ),
            )
            return existing.message_id

        message = await self.bot.send_message(
            chat_id=chat_id,
            text=item.text,
            reply_markup=markup,
            message_thread_id=item.message_thread_id,
            parse_mode="HTML",
        )
        if item.correlation_key:
            async with self.uow as uow:
                await uow.messages.upsert(
                    item.correlation_key, chat_id, message.message_id
                )
                await uow.commit(True)
        return message.message_id

    @staticmethod
    def _markup(item: TelegramDeliveryItem) -> InlineKeyboardMarkup | None:
        if not item.buttons:
            return None
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button.text, callback_data=button.callback_data
                    )
                    for button in row
                ]
                for row in item.buttons
            ]
        )

    @staticmethod
    def _is_expired(item: TelegramDeliveryItem) -> bool:
        return (
            item.expires_at is not None
            and item.expires_at < datetime.now(timezone.utc)
        )
