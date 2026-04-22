from fastapi_mail import MessageSchema, MessageType
from logging import getLogger

from mail.utils.emails import get_fastmail

from core.broker.kafka import KafkaRouter
from core.enum.mq import EmailQueue
from core.schema.message.mail import SendVerifyMessageRequest

router = KafkaRouter()


logger = getLogger(__name__)


@router.subscriber(EmailQueue.VERIFY)
async def send_verify_message(request: SendVerifyMessageRequest) -> None:
    with open("static/email/verify_message.html", "r") as f:
        html = f.read().replace("{{token}}", request.token)
    message = MessageSchema(
        subject="Thanks for using Project Capillary",
        recipients=[request.email],
        body=html,
        subtype=MessageType.html,
    )
    try:
        await get_fastmail().send_message(message)
    except Exception as e:
        logger.error(f"Error sending verify message: {e}")
