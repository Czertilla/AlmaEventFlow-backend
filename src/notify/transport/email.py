from uuid import UUID

from core.enum.mq import NotifyDeliveryQueue
from core.enum.notify import TransportTypeEnum
from core.schema.message.notify import EmailDeliveryBatch, EmailDeliveryItem

from notify.config.settings import settings
from notify.transport.base import DelegatedTransport, DeliveryDraft


class EmailTransport(DelegatedTransport):
    """Guaranteed transport. Builds a self-contained ``EmailDeliveryBatch`` for
    the ``mail`` service; recipient addresses come from the account projection
    resolved at ingest time, so ``mail`` needs no database access."""

    type = TransportTypeEnum.email
    label = "Email"
    delivery_topic = NotifyDeliveryQueue.EMAIL
    template = "notification"

    def batch_size(self) -> int:
        return settings.EMAIL_DELIVERY_BATCH_SIZE

    def build_batch(
        self, notification_id: UUID, drafts: list[DeliveryDraft]
    ) -> EmailDeliveryBatch:
        items = [self._item(draft) for draft in drafts]
        return EmailDeliveryBatch(
            notification_id=notification_id,
            transport=self.type,
            delivery_ids=[item.delivery_id for item in items],
            items=items,
        )

    def _item(self, draft: DeliveryDraft) -> EmailDeliveryItem:
        content = draft.ctx.content
        return EmailDeliveryItem(
            delivery_id=draft.delivery_id,
            recipient=draft.ctx.account.email,
            subject=content.title,
            template=self.template,
            context={
                "title": content.title,
                "body": content.body,
                "action_url": content.action_url or "",
            },
            expires_at=draft.ctx.expires_at,
        )
