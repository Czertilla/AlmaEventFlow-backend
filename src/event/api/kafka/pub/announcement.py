from core.broker.kafka import KafkaRouter
from core.enum.mq import AnnouncementQueue
from core.utils.announcement import send_announcement

router = KafkaRouter()


send_announcement = router.publisher(AnnouncementQueue.COLLECTIVE_REQUESTED)(
    send_announcement
)
