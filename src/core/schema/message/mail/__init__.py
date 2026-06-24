from pydantic import EmailStr, Field
from core.schema.message.core import MQRequest


class SendVerifyMessageRequest(MQRequest):
    token: str
    email: EmailStr


class SendTemplatedEmailRequest(MQRequest):
    """Generic templated email send. The ``mail`` service owns the templates,
    renders ``template`` with ``context`` and sends it."""

    template: str
    subject: str
    recipients: list[EmailStr] = Field(min_length=1)
    context: dict[str, str] = Field(default_factory=dict)
