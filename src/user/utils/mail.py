from logging import getLogger

from fastapi.responses import JSONResponse
from pydantic import EmailStr

from core.broker.kafka import KafkaBroker, broker
from core.enum.mq import EmailQueue
from core.schema.message.mail import (
    SendResetPasswordMessageRequest,
    SendVerifyMessageRequest,
)

logger = getLogger(__name__)


async def send_verify_message(
    email: EmailStr, token: str, broker: KafkaBroker = broker
) -> JSONResponse:
    logger.debug("Sending verify message to %s with token", email)
    await broker.publish(
        SendVerifyMessageRequest(email=email, token=token),
        EmailQueue.VERIFY,
    )
    return JSONResponse(content="OK")


async def send_reset_message(
    email: EmailStr, token: str, broker: KafkaBroker = broker
) -> JSONResponse:
    logger.debug("Sending password reset message to %s with token", email)
    await broker.publish(
        SendResetPasswordMessageRequest(email=email, token=token),
        EmailQueue.RESET,
    )
    return JSONResponse(content="OK")
