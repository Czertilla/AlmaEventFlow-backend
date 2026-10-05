from logging import getLogger

from core.broker.kafka import KafkaBroker, broker
from core.config.settings import settings
from core.enum.mq import AnnouncementQueue
from core.schema.message.announcement import AnnouncementRequest

logger = getLogger(__name__)


async def send_announcement(
    request: AnnouncementRequest, broker: KafkaBroker = broker
) -> None:
    logger.info(
        "Publishing announcement: topic=%s event=%s collective=%s "
        "transport=%s",
        AnnouncementQueue.COLLECTIVE_REQUESTED,
        request.event_id,
        request.collective_id,
        "in-memory" if settings.IN_MEMORY_BROKER else "kafka",
    )
    logger.debug(f"Sending announcement request {request=}")
    await broker.publish(request, AnnouncementQueue.COLLECTIVE_REQUESTED)
