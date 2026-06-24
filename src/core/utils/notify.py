from logging import getLogger

from fastapi.responses import JSONResponse
from pydantic import EmailStr

from core.broker.kafka import broker, KafkaBroker
from core.schema.message.notify import NotificationRequest
from core.enum.mq import NotifyQueue


logger = getLogger(__name__)


async def send_notification(
    notification_request: NotificationRequest, broker: KafkaBroker = broker
) -> None:
    logger.debug(f"Sending notification request {notification_request=}")
    await broker.publish(
        notification_request,
        NotifyQueue.SEND,
    )
