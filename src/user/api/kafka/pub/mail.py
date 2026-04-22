from fastapi.responses import JSONResponse
from core.broker.kafka import broker, KafkaBroker, KafkaRouter
from core.schema.message.mail import SendVerifyMessageRequest
from core.enum.mq import EmailQueue
from pydantic import EmailStr
from logging import getLogger

logger = getLogger(__name__)


router = KafkaRouter()


@router.publisher(EmailQueue.VERIFY)
async def send_verify_message(
    email: EmailStr, token: str, broker: KafkaBroker = broker
) -> SendVerifyMessageRequest:
    logger.debug(f"Sending verify message to {email} with token")
    await broker.publish(
        message=SendVerifyMessageRequest(email=email, token=token),
        queue=EmailQueue.VERIFY,
    )
    return JSONResponse(content="OK")
