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

    TELEGRAM = "delivery.telegram"
    """Telegram transport batch. Payload: ``TelegramDeliveryBatch`` (a group of
    deliveries with inline chat_id/text/buttons). Consumed by the ``bot``
    service, which owns the actual Bot API send/edit and message-id
    correlation."""

    EMAIL_DLQ = "delivery.email.dlq"
    WEBPUSH_DLQ = "delivery.web_push.dlq"
    TELEGRAM_DLQ = "delivery.telegram.dlq"


@prefix("announcements/")
class AnnouncementQueue(StrEnum):
    """Group/collective chat announcements — deliberately separate from
    notify's personal-notification pipeline (see ``src/notify/TECH_TASK.md``
    §5.3: a collective's shared chat is not a personal delivery target).
    Published directly by domain services; consumed by ``bot``, which owns
    the collective→chat_id mapping and the Bot API delivery itself."""

    COLLECTIVE_REQUESTED = "collective.requested"
    """Payload: ``AnnouncementRequest``. Published by ``event`` on the same
    triggers as the personal attendance notification (event created/became
    active, or a material edit to an already-active event)."""

    COLLECTIVE_REQUESTED_DLQ = "collective.requested.dlq"


def dlq_for(topic: str) -> str:
    """Dead-letter topic for any transport/delivery topic (``<topic>.dlq``)."""
    return f"{topic}.dlq"