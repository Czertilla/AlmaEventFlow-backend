from logging import getLogger

from core.broker.kafka import KafkaBroker, broker
from core.enum.mq import NotifyQueue
from core.schema.message.notify import NotificationRequest

logger = getLogger(__name__)


async def send_notification(
    notification_request: NotificationRequest, broker: KafkaBroker = broker
) -> None:
    logger.debug(f"Sending notification request {notification_request=}")
    await broker.publish(
        notification_request,
        NotifyQueue.SEND,
    )
