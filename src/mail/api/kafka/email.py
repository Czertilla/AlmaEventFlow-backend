import asyncio
from datetime import UTC, datetime
from logging import getLogger

from fastapi_mail import MessageSchema, MessageType

from core.broker.kafka import KafkaRouter, broker
from core.enum.mq import EmailQueue, NotifyDeliveryQueue
from core.enum.notify import DeliveryStatus
from core.schema.message.mail import (
    SendResetPasswordMessageRequest,
    SendTemplatedEmailRequest,
    SendVerifyMessageRequest,
)
from core.schema.message.notify import (
    DeliveryResult,
    EmailDeliveryBatch,
    EmailDeliveryItem,
)
from mail.utils.emails import get_fastmail
from mail.utils.templates import render_template

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


async def _send(subject: str, recipients: list[str], html: str, what: str) -> None:
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=html,
        subtype=MessageType.html,
    )
    try:
        await get_fastmail().send_message(message)
    except Exception as e:
        logger.error("Error sending %s: %s", what, e)


@router.subscriber(EmailQueue.VERIFY)
async def send_verify_message(request: SendVerifyMessageRequest) -> None:
    html = render_template("verify_message", {"token": request.token})
    await _send(
        "Alma Event Flow email confirmation",
        [request.email],
        html,
        "verify message",
    )


@router.subscriber(EmailQueue.RESET)
async def send_reset_password_message(
    request: SendResetPasswordMessageRequest,
) -> None:
    html = render_template("reset_message", {"token": request.token})
    await _send(
        "Alma Event Flow password reset",
        [request.email],
        html,
        "password reset message",
    )


@router.subscriber(EmailQueue.SEND)
async def send_templated_message(request: SendTemplatedEmailRequest) -> None:
    """Generic templated email delivery used by the notify service."""
    try:
        html = render_template(request.template, request.context)
    except Exception as e:
        logger.error("Error rendering template %r: %s", request.template, e)
        return
    await _send(request.subject, request.recipients, html, "templated message")


def _is_expired(item: EmailDeliveryItem) -> bool:
    return (
        item.expires_at is not None
        and item.expires_at < datetime.now(UTC)
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
        logger.error("Error rendering template %r: %s", item.template, e)
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
        logger.error("Error sending notification email: %s", e)
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
