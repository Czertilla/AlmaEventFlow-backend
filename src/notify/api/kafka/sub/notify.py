from logging import getLogger

from faststream import Depends

from core.broker.kafka import KafkaRouter, broker
from core.dependencies.uow import ModuleUOWDep
from core.enum.mq import NotifyQueue
from core.schema.message.notify import NotificationRequest

from notify.service.dispatch import NotificationService
from notify.uow.notify import NotifyUOW

logger = getLogger(__name__)

router = KafkaRouter()

NotifyUOWDep = Depends(ModuleUOWDep("notify")(NotifyUOW))


@router.subscriber(NotifyQueue.SEND)
async def on_notification(request: NotificationRequest, uow=NotifyUOWDep):
    """Single inbound async API: producers publish a ``NotificationRequest``.
    Ingest runs in one transaction, so a failure leaves nothing persisted and
    the request is dead-lettered for inspection."""
    try:
        await NotificationService(uow).dispatch(request)
    except Exception:
        logger.exception("Ingest failed for event %s", request.event_id)
        await broker.publish(request, NotifyQueue.SEND_DLQ)
