import asyncio
from datetime import datetime, timezone
from fastapi_mail import MessageSchema, MessageType
from logging import getLogger

from mail.utils.emails import get_fastmail
from mail.utils.templates import render_template

from core.broker.kafka import KafkaRouter, broker
from core.enum.mq import EmailQueue, NotifyDeliveryQueue
from core.enum.notify import DeliveryStatus
from core.schema.message.mail import (
    SendTemplatedEmailRequest,
    SendVerifyMessageRequest,
)
from core.schema.message.notify import (
    DeliveryResult,
    EmailDeliveryBatch,
    EmailDeliveryItem,
)

router = KafkaRouter()


logger = getLogger(__name__)

EMAIL_SEND_CONCURRENCY = 10
"""Upper bound on simultaneous provider sends per batch, so a large batch does
not open one SMTP connection per recipient at once."""


async def _report(
    delivery_id, status: DeliveryStatus, error: str | None = None
) -> None:
    await broker.publish(
        DeliveryResult(delivery_id=delivery_id, status=status, error=error),
        NotifyDeliveryQueue.RESULT,
    )


@router.subscriber(EmailQueue.VERIFY)
async def send_verify_message(request: SendVerifyMessageRequest) -> None:
    with open(
        "templates/email/verify_message.html", "r", encoding="utf-8"
    ) as f:
        html = f.read().replace("{{token}}", request.token)
    message = MessageSchema(
        subject="Alma Event Flow email confirmation",
        recipients=[request.email],
        body=html,
        subtype=MessageType.html,
    )
    try:
        await get_fastmail().send_message(message)
    except Exception as e:
        logger.error(f"Error sending verify message: {e}")


@router.subscriber(EmailQueue.SEND)
async def send_templated_message(request: SendTemplatedEmailRequest) -> None:
    """Generic templated email delivery used by the notify service."""
    try:
        html = render_template(request.template, request.context)
    except Exception as e:
        logger.error(f"Error rendering template {request.template!r}: {e}")
        return
    message = MessageSchema(
        subject=request.subject,
        recipients=request.recipients,
        body=html,
        subtype=MessageType.html,
    )
    try:
        await get_fastmail().send_message(message)
    except Exception as e:
        logger.error(f"Error sending templated message: {e}")


def _is_expired(item: EmailDeliveryItem) -> bool:
    return (
        item.expires_at is not None
        and item.expires_at < datetime.now(timezone.utc)
    )


async def _deliver_item(item: EmailDeliveryItem) -> None:
    """Renders and sends one delivery, reporting its individual outcome. A
    per-recipient failure never aborts the rest of the batch."""
    if _is_expired(item):
        await _report(item.delivery_id, DeliveryStatus.expired, "expired")
        return
    try:
        html = render_template(item.template, item.context)
    except Exception as e:
        logger.error(f"Error rendering template {item.template!r}: {e}")
        await _report(item.delivery_id, DeliveryStatus.failed, "render_error")
        return
    message = MessageSchema(
        subject=item.subject,
        recipients=[item.recipient],
        body=html,
        subtype=MessageType.html,
    )
    try:
        await get_fastmail().send_message(message)
    except Exception as e:
        logger.error(f"Error sending notification email: {e}")
        await _report(item.delivery_id, DeliveryStatus.retry_scheduled, str(e))
        return
    await _report(item.delivery_id, DeliveryStatus.sent)


@router.subscriber(NotifyDeliveryQueue.EMAIL)
async def deliver_notification_email(batch: EmailDeliveryBatch) -> None:
    """Handles an email transport batch: sends deliveries concurrently (bounded)
    and persists the result per ``notification_delivery`` (never per batch)."""
    logger.info(
        "Email batch %s: %d deliveries", batch.message_id, len(batch.items)
    )
    semaphore = asyncio.Semaphore(EMAIL_SEND_CONCURRENCY)

    async def _bounded(item: EmailDeliveryItem) -> None:
        async with semaphore:
            await _deliver_item(item)

    try:
        await asyncio.gather(*(_bounded(item) for item in batch.items))
    except Exception:
        logger.exception("Email batch %s failed", batch.message_id)
        await broker.publish(batch, NotifyDeliveryQueue.EMAIL_DLQ)
