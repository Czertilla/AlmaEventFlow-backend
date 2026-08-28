from html import escape
from uuid import UUID

from core.enum.mq import NotifyDeliveryQueue
from core.enum.notify import NotificationCategory, TransportTypeEnum
from core.schema.message.notify import (
    TelegramButton,
    TelegramDeliveryBatch,
    TelegramDeliveryItem,
)
from notify.exc import TelegramClientInvalidException
from notify.schema.notification import NotificationContent
from notify.transport.base import BaseTransport, DeliveryDraft


class TelegramTransport(BaseTransport):
    """Personal Telegram DMs. Delegated to the ``bot`` service (which owns the
    Bot API token, message-id correlation and edit-in-place logic), but still
    requires a registered ``client`` — the chat_id — unlike guaranteed email.
    Group/collective chat announcements are a separate, non-personal pipeline
    (``announcements.collective.requested``) and never go through this
    transport; see ``src/notify/TECH_TASK.md``."""

    type = TransportTypeEnum.telegram
    label = "Telegram"
    delivery_topic = NotifyDeliveryQueue.TELEGRAM
    delegated = True
    requires_client = True

    def validate_client_payload(self, payload: dict[str, str]) -> dict[str, str]:
        chat_id = payload.get("chat_id")
        if not chat_id:
            raise TelegramClientInvalidException()
        return {"chat_id": str(chat_id)}

    def build_batch(
        self, notification_id: UUID, drafts: list[DeliveryDraft]
    ) -> TelegramDeliveryBatch:
        items = [self._item(draft) for draft in drafts]
        return TelegramDeliveryBatch(
            notification_id=notification_id,
            transport=self.type,
            delivery_ids=[item.delivery_id for item in items],
            items=items,
        )

    def _item(self, draft: DeliveryDraft) -> TelegramDeliveryItem:
        content = draft.ctx.content
        return TelegramDeliveryItem(
            delivery_id=draft.delivery_id,
            chat_id=draft.target.client.endpoint,
            text=self._render_text(content),
            buttons=self._render_buttons(content),
            correlation_key=content.data.get("event_id"),
            expires_at=draft.ctx.expires_at,
        )

    @staticmethod
    def _render_text(content: NotificationContent) -> str:
        # The bot sends with parse_mode=HTML, and title/body now routinely
        # carry free-text event descriptions -- escape so a stray `<`/`&` in
        # someone's event text doesn't break the whole send.
        title = escape(content.title) if content.title else ""
        parts = [f"<b>{title}</b>"] if title else []
        if content.body:
            parts.append(escape(content.body))
        if content.action_url:
            parts.append(escape(content.action_url))
        return "\n\n".join(parts) or title

    @staticmethod
    def _render_buttons(
        content: NotificationContent,
    ) -> list[list[TelegramButton]]:
        if content.category != NotificationCategory.attendance:
            return []
        event_id = content.data.get("event_id")
        if not event_id:
            return []
        return [
            [
                TelegramButton(
                    text="✅ Буду", callback_data=f"att:{event_id}:yes"
                ),
                TelegramButton(
                    text="❌ Не буду", callback_data=f"att:{event_id}:no"
                ),
            ]
        ]
