from enum import StrEnum


from core.utils.enum.prefix import prefix


@prefix("mail/")
class EmailQueue(StrEnum):
    VERIFY = "verify"
    RESET = "reset"
    """Password reset email. Payload: ``SendResetPasswordMessageRequest``.
    Published by the ``user`` service on a forgot-password request."""
    SEND = "send"
    """Generic templated email send. Payload: ``SendTemplatedEmailRequest``.
    Used by ``notify`` to delegate arbitrary email delivery to the ``mail``
    service, which owns the templates."""


@prefix("notify/")
class NotifyQueue(StrEnum):
    """Single inbound async API of the notify service. Producers publish a
    ``NotificationRequest`` to ``NotifyQueue.SEND``."""

    SEND = "send"

    SEND_DLQ = "send.dlq"
    """Dead-letter for notification requests that could not be ingested."""


@prefix("notify/")
class NotifyDeliveryQueue(StrEnum):
    """Internal delivery topics filled by the notify outbox publisher. Each
    transport drains its own topic; specialized workers consume it and report
    back to ``RESULT``."""

    EMAIL = "delivery.email"
    """Email transport batch. Payload: ``EmailDeliveryBatch`` (a group of
    deliveries with inline content). Consumed by the ``mail`` service."""

    WEBPUSH = "delivery.web_push"
    """Web push transport batch. Payload: ``WebPushDeliveryBatch``. Consumed by
    the in-notify web push worker."""

    RESULT = "delivery.result"
    """Delivery outcome reported by external workers. Payload:
    ``DeliveryResult``. Consumed by notify to update delivery status."""

    EMAIL_DLQ = "delivery.email.dlq"
    WEBPUSH_DLQ = "delivery.web_push.dlq"


def dlq_for(topic: str) -> str:
    """Dead-letter topic for any transport/delivery topic (``<topic>.dlq``)."""
    return f"{topic}.dlq"