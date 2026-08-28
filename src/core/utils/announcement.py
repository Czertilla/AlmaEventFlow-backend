from logging import getLogger

from core.broker.kafka import KafkaBroker, broker
from core.enum.mq import AnnouncementQueue
from core.schema.message.announcement import AnnouncementRequest

logger = getLogger(__name__)


async def send_announcement(
    request: AnnouncementRequest, broker: KafkaBroker = broker
) -> None:
    logger.debug(f"Sending announcement request {request=}")
    await broker.publish(request, AnnouncementQueue.COLLECTIVE_REQUESTED)
