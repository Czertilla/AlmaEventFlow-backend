from pydantic import EmailStr
from core.schema.message.core import MQRequest


class SendVerifyMessageRequest(MQRequest):
    token: str
    email: EmailStr
