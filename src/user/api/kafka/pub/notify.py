from core.broker.kafka import KafkaRouter
from core.enum.mq import NotifyQueue

from core.utils.notify import send_notification


router = KafkaRouter()


send_notification = router.publisher(NotifyQueue.SEND)(send_notification)