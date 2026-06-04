from logging import getLogger

from fastapi.responses import JSONResponse
from pydantic import EmailStr

from core.broker.kafka import broker, KafkaBroker
from core.schema.message.mail import SendVerifyMessageRequest
from core.enum.mq import EmailQueue


logger = getLogger(__name__)


async def send_verify_message(
    email: EmailStr, token: str, broker: KafkaBroker = broker
) -> JSONResponse:
    logger.debug(f"Sending verify message to {email} with token")
    await broker.publish(
        SendVerifyMessageRequest(email=email, token=token),
        EmailQueue.VERIFY,
    )
    return JSONResponse(content="OK")
