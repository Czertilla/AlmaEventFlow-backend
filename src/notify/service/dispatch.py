from collections import defaultdict
from logging import getLogger
from uuid import UUID

from core.enum.notify import DeliveryStatus, TransportTypeEnum
from core.schema.message.notify import NotificationRequest
from core.service.base import BaseService, required_transaction

from notify.config.settings import settings
from notify.models.notification import NotificationORM
from notify.models.recipient import NotificationRecipientORM
from notify.schema.account import AccountRead
from notify.schema.client import ClientTarget
from notify.schema.notification import NotificationContent
from notify.service.batching import build_outbox_rows
from notify.transport import registry
from notify.transport.base import (
    BaseTransport,
    DeliveryDraft,
    DeliveryTarget,
    PlanContext,
)
from notify.uow.notify import NotifyUOW

logger = getLogger(__name__)

DraftsByTransport = dict[TransportTypeEnum, list[DeliveryDraft]]


class NotificationService(BaseService[NotifyUOW]):
    """Ingest stage: idempotently persists a ``NotificationRequest`` as a
    notification, its recipients and per-user/endpoint deliveries, then groups
    those deliveries into transport batch messages in the outbox — all in one
    transaction. Physical delivery is handled later by the outbox publisher and
    the transport workers."""

    async def dispatch(self, request: NotificationRequest) -> None:
        async with self.uow as uow:
            created = await self._ingest(request)
            if created:
                await uow.commit()

    @required_transaction
    async def _ingest(self, request: NotificationRequest) -> bool:
        if await self.uow.notifications.get_by_event_id(request.event_id):
            logger.info("Duplicate notification %s ignored", request.event_id)
            return False
        notification = await self.uow.notifications.add_n_return(
            {
                "event_id": request.event_id,
                "category": request.category,
                "title": request.title,
                "body": request.body,
                "action_url": request.action_url,
                "data": request.data,
                "expires_at": request.expires_at,
            }
        )
        content = NotificationContent.from_request(request)
        forced = set(request.transports) if request.transports else None
        drafts: DraftsByTransport = defaultdict(list)
        for user_id in request.user_ids:
            await self._plan_recipient(
                notification, user_id, content, forced, drafts
            )
        await self._enqueue_batches(notification.id, drafts)
        return True

    @required_transaction
    async def _plan_recipient(
        self,
        notification: NotificationORM,
        user_id: UUID,
        content: NotificationContent,
        forced: set[TransportTypeEnum] | None,
        drafts: DraftsByTransport,
    ) -> None:
        recipient = await self.uow.recipients.add_n_return(
            {"notification_id": notification.id, "user_id": user_id}
        )
        ctx = PlanContext(
            notification_id=notification.id,
            user_id=user_id,
            content=content,
            account=await self._account(user_id),
            expires_at=notification.expires_at,
        )
        prefs = await self._resolve_prefs(user_id)
        for transport in registry.all_transports():
            await self._plan_transport(
                transport, recipient, ctx, prefs, forced, drafts
            )

    @required_transaction
    async def _plan_transport(
        self,
        transport: BaseTransport,
        recipient: NotificationRecipientORM,
        ctx: PlanContext,
        prefs: dict[TransportTypeEnum, bool],
        forced: set[TransportTypeEnum] | None,
        drafts: DraftsByTransport,
    ) -> None:
        ttype = transport.type
        if forced is not None and ttype not in forced:
            return
        if not prefs.get(ttype, False) or not transport.is_available():
            return
        targets = await self._targets(transport, ctx)
        if not targets:
            if not transport.requires_client:
                await self._record_unresolved(transport, recipient, ctx)
            return
        for target in targets:
            await self._create_delivery(transport, recipient, ctx, target, drafts)

    @required_transaction
    async def _create_delivery(
        self,
        transport: BaseTransport,
        recipient: NotificationRecipientORM,
        ctx: PlanContext,
        target: DeliveryTarget,
        drafts: DraftsByTransport,
    ) -> None:
        delivery = await self.uow.deliveries.add_n_return(
            {
                "notification_id": ctx.notification_id,
                "recipient_id": recipient.id,
                "user_id": ctx.user_id,
                "transport": transport.type,
                "client_id": target.client.id if target.client else None,
                "status": DeliveryStatus.pending,
                "max_attempts": settings.DELIVERY_MAX_ATTEMPTS,
            }
        )
        drafts[transport.type].append(
            DeliveryDraft(delivery_id=delivery.id, ctx=ctx, target=target)
        )

    @required_transaction
    async def _enqueue_batches(
        self, notification_id: UUID, drafts: DraftsByTransport
    ) -> None:
        for row in build_outbox_rows(notification_id, drafts):
            await self.uow.outbox.add_one(
                {"topic": row.topic, "payload": row.payload}
            )

    @required_transaction
    async def _record_unresolved(
        self,
        transport: BaseTransport,
        recipient: NotificationRecipientORM,
        ctx: PlanContext,
    ) -> None:
        logger.warning(
            "No address for transport %s, user %s", transport.type, ctx.user_id
        )
        await self.uow.deliveries.add_one(
            {
                "notification_id": ctx.notification_id,
                "recipient_id": recipient.id,
                "user_id": ctx.user_id,
                "transport": transport.type,
                "status": DeliveryStatus.failed,
                "max_attempts": settings.DELIVERY_MAX_ATTEMPTS,
                "last_error": "address_unresolved",
            }
        )

    async def _targets(
        self, transport: BaseTransport, ctx: PlanContext
    ) -> list[DeliveryTarget]:
        if transport.requires_client:
            rows = await self.uow.clients.get_active(ctx.user_id, transport.type)
            return [
                DeliveryTarget(client=ClientTarget.model_validate(row))
                for row in rows
            ]
        if ctx.account is None or not ctx.account.email:
            return []
        return [DeliveryTarget(client=None)]

    async def _account(self, user_id: UUID) -> AccountRead | None:
        row = await self.uow.accounts.get_by_id(user_id)
        return AccountRead.model_validate(row) if row is not None else None

    async def _resolve_prefs(
        self, user_id: UUID
    ) -> dict[TransportTypeEnum, bool]:
        prefs: dict[TransportTypeEnum, bool] = {
            transport.type: (transport.type in registry.DEFAULT_ENABLED)
            for transport in registry.all_transports()
        }
        for row in await self.uow.preferences.get_by_user(user_id):
            prefs[row.transport] = row.is_enabled
        prefs[registry.GUARANTEED] = True
        return prefs
