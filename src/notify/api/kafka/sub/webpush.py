from logging import getLogger

from faststream import Depends

from core.broker.kafka import KafkaRouter, broker
from core.dependencies.uow import ModuleUOWDep
from core.enum.mq import NotifyDeliveryQueue
from core.schema.message.notify import WebPushDeliveryBatch

from notify.service.webpush import WebPushWorkerService
from notify.uow.delivery import WebPushDeliveryUOW

logger = getLogger(__name__)

router = KafkaRouter()

WebPushUOWDep = Depends(ModuleUOWDep("notify")(WebPushDeliveryUOW))


@router.subscriber(NotifyDeliveryQueue.WEBPUSH)
async def on_web_push(batch: WebPushDeliveryBatch, uow=WebPushUOWDep):
    try:
        await WebPushWorkerService(uow).handle(batch)
    except Exception:
        logger.exception("Web push batch %s failed", batch.message_id)
        await broker.publish(batch, NotifyDeliveryQueue.WEBPUSH_DLQ)
