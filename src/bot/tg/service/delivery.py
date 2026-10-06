import re
from datetime import UTC, datetime
from logging import getLogger

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramMigrateToChat,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramUnauthorizedError,
)
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyParameters,
)

from bot.tg.model.message import TelegramMessageORM
from bot.tg.uow.message import TelegramMessageUOW
from core.enum.notify import DeliveryStatus
from core.schema.message.notify import (
    DeliveryResult,
    TelegramButton,
    TelegramDeliveryItem,
)
from core.service.base import BaseService

logger = getLogger(__name__)

UPDATED_PING_TEXT = "🔄 Обновлено"

RETRY_AFTER_PREFIX = "retry_after:"

_TG_TIME = re.compile(r"<tg-time[^>]*>(.*?)</tg-time>", re.DOTALL)


def strip_tg_time(text: str) -> str:
    return _TG_TIME.sub(lambda match: match.group(1), text)


def _entities_rejected(exc: TelegramBadRequest, text: str) -> bool:
    return "parse entities" in str(exc).lower() and "<tg-time" in text


def _button_url_rejected(exc: TelegramBadRequest) -> bool:
    return "button_url_invalid" in str(exc).lower()


def _without_links(
    rows: list[list[TelegramButton]],
) -> list[list[TelegramButton]]:
    kept = [[b for b in row if b.url is None] for row in rows]
    return [row for row in kept if row]


_EDIT_TARGET_GONE = (
    "message to edit not found",
    "message can't be edited",
    "message_id_invalid",
)


class ChatMigratedError(Exception):
    """A group chat was upgraded to a supergroup, so Telegram gave it a new
    id and the old one no longer accepts messages."""

    def __init__(self, old_chat_id: int, new_chat_id: int) -> None:
        super().__init__(f"chat {old_chat_id} migrated to {new_chat_id}")
        self.old_chat_id = old_chat_id
        self.new_chat_id = new_chat_id


def _edit_target_gone(exc: TelegramBadRequest) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in _EDIT_TARGET_GONE)


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
            logger.info(
                "Telegram delivery %s to chat %s expired, skipped",
                item.delivery_id,
                item.chat_id,
            )
            return DeliveryResult(
                delivery_id=item.delivery_id,
                status=DeliveryStatus.expired,
                error="expired",
            )
        chat_id = int(item.chat_id)
        markup = self._markup(item)
        existing = await self._existing_message(item, chat_id)
        logger.info(
            "Telegram delivery %s: chat=%s mode=%s correlation=%s thread=%s "
            "text_length=%d",
            item.delivery_id,
            chat_id,
            "edit" if existing is not None else "send",
            item.correlation_key,
            item.message_thread_id,
            len(item.text),
        )
        try:
            message_id = await self._send_or_edit(
                item, chat_id, markup, existing
            )
        except TelegramMigrateToChat as exc:
            logger.warning(
                "Telegram chat %s was migrated to supergroup %s",
                chat_id,
                exc.migrate_to_chat_id,
            )
            raise ChatMigratedError(chat_id, exc.migrate_to_chat_id) from exc
        except TelegramRetryAfter as exc:
            logger.warning(
                "Telegram flood control for chat %s: retry after %s s",
                chat_id,
                exc.retry_after,
            )
            return DeliveryResult(
                delivery_id=item.delivery_id,
                status=DeliveryStatus.retry_scheduled,
                error=f"{RETRY_AFTER_PREFIX}{exc.retry_after}",
            )
        except TelegramUnauthorizedError as exc:
            logger.error(
                "Telegram rejected the bot token while sending to chat %s: %s",
                chat_id,
                exc,
            )
            return DeliveryResult(
                delivery_id=item.delivery_id,
                status=DeliveryStatus.retry_scheduled,
                error="unauthorized",
            )
        except TelegramNotFound as exc:
            logger.warning(
                "Telegram chat %s not found (deleted, or the bot was "
                "removed): %s",
                chat_id,
                exc,
            )
            return DeliveryResult(
                delivery_id=item.delivery_id,
                status=DeliveryStatus.failed,
                error=str(exc),
            )
        except TelegramForbiddenError as exc:
            logger.warning("Telegram forbidden for chat %s: %s", chat_id, exc)
            return DeliveryResult(
                delivery_id=item.delivery_id,
                status=DeliveryStatus.failed,
                error="forbidden",
            )
        except TelegramBadRequest as exc:
            if _entities_rejected(exc, item.text):
                logger.warning(
                    "Telegram rejected date entities for chat %s, resending "
                    "as plain text",
                    chat_id,
                )
                return await self.deliver(
                    item.model_copy(
                        update={"text": strip_tg_time(item.text)}
                    )
                )
            if _button_url_rejected(exc) and any(
                button.url for row in item.buttons for button in row
            ):
                logger.warning(
                    "Telegram rejected a link button for chat %s, resending "
                    "without links",
                    chat_id,
                )
                return await self.deliver(
                    item.model_copy(
                        update={"buttons": _without_links(item.buttons)}
                    )
                )
            if existing is not None and "message is not modified" in str(
                exc
            ).lower():
                # Redelivered batch with unchanged content — not an error.
                logger.info(
                    "Telegram message %s in chat %s is already up to date",
                    existing.message_id,
                    chat_id,
                )
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
        logger.info(
            "Telegram delivery %s done: chat=%s message=%s",
            item.delivery_id,
            chat_id,
            message_id,
        )
        return DeliveryResult(
            delivery_id=item.delivery_id,
            status=DeliveryStatus.sent,
            provider_message_id=str(message_id),
        )

    async def _existing_message(
        self, item: TelegramDeliveryItem, chat_id: int
    ) -> TelegramMessageORM | None:
        if not item.correlation_key:
            return None
        async with self.uow as uow:
            return await uow.messages.get(item.correlation_key, chat_id)

    async def _send_or_edit(
        self,
        item: TelegramDeliveryItem,
        chat_id: int,
        markup: InlineKeyboardMarkup | None,
        existing: TelegramMessageORM | None,
    ) -> int:
        if existing is not None:
            try:
                await self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=existing.message_id,
                    text=item.text,
                    reply_markup=markup,
                    parse_mode="HTML",
                )
            except TelegramBadRequest as exc:
                if not _edit_target_gone(exc):
                    raise
                logger.warning(
                    "Telegram message %s in chat %s can't be edited (%s), "
                    "sending a new one",
                    existing.message_id,
                    chat_id,
                    exc,
                )
                return await self._send_new(item, chat_id, markup)
            await self.bot.send_message(
                chat_id=chat_id,
                text=item.edit_ping or UPDATED_PING_TEXT,
                disable_notification=item.disable_notification or None,
                reply_parameters=ReplyParameters(
                    message_id=existing.message_id,
                    allow_sending_without_reply=True,
                ),
            )
            return existing.message_id
        return await self._send_new(item, chat_id, markup)

    async def _send_new(
        self,
        item: TelegramDeliveryItem,
        chat_id: int,
        markup: InlineKeyboardMarkup | None,
    ) -> int:
        message = await self.bot.send_message(
            chat_id=chat_id,
            text=item.text,
            reply_markup=markup,
            message_thread_id=item.message_thread_id,
            disable_notification=item.disable_notification or None,
            parse_mode="HTML",
        )
        if item.correlation_key:
            async with self.uow as uow:
                await uow.messages.upsert(
                    item.correlation_key, chat_id, message.message_id
                )
                await uow.commit(True)
        if item.pin:
            await self._pin(chat_id, message.message_id)
        return message.message_id

    async def _pin(self, chat_id: int, message_id: int) -> None:
        try:
            await self.bot.pin_chat_message(
                chat_id=chat_id,
                message_id=message_id,
                disable_notification=True,
            )
        except TelegramAPIError as exc:
            logger.warning(
                "could not pin message %s in chat %s: %s",
                message_id,
                chat_id,
                exc,
            )

    @staticmethod
    def _markup(item: TelegramDeliveryItem) -> InlineKeyboardMarkup | None:
        if not item.buttons:
            return None
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button.text,
                        callback_data=button.callback_data,
                        url=button.url,
                        style=button.style,
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
            and item.expires_at < datetime.now(UTC)
        )
