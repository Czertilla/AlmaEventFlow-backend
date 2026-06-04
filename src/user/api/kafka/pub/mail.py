from core.broker.kafka import KafkaRouter
from core.enum.mq import EmailQueue

from user.utils.mail import send_verify_message


router = KafkaRouter()


send_verify_message = router.publisher(EmailQueue.VERIFY)(send_verify_message)
