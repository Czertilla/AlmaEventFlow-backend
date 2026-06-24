from datetime import datetime, timedelta, timezone
from uuid import uuid4

from core.enum.notify import (
    DeliveryStatus,
    NotificationCategory,
    TransportTypeEnum,
)
from core.schema.message.notify import NotificationRequest

from notify.config.settings import settings
from notify.models.delivery import NotificationDeliveryORM
from notify.models.notification import NotificationORM
from notify.models.outbox import OutboxEventORM
from notify.models.recipient import NotificationRecipientORM
from notify.service.dispatch import NotificationService
from notify.service.reenqueue import RetryReenqueueService
from notify.uow.notify import NotifyUOW
from notify.uow.outbox import RetryUOW


def _email_request(user_ids) -> NotificationRequest:
    return NotificationRequest(
        user_ids=user_ids,
        title="Subject",
        body="Body",
        transports=[TransportTypeEnum.email],
    )


async def test_thirty_recipients_one_email_batch(sessionmaker_, seed):
    user_ids = await seed.accounts(30)
    await NotificationService(NotifyUOW(sessionmaker_)).dispatch(
        _email_request(user_ids)
    )

    assert await seed.count(NotificationDeliveryORM) == 30
    outbox = await seed.all(OutboxEventORM)
    assert len(outbox) == 1
    assert len(outbox[0].payload["delivery_ids"]) == 30
    assert outbox[0].payload["transport"] == TransportTypeEnum.email.value


async def test_seventy_recipients_split_into_two_batches(
    sessionmaker_, seed, monkeypatch
):
    monkeypatch.setattr(settings, "EMAIL_DELIVERY_BATCH_SIZE", 50)
    user_ids = await seed.accounts(70)
    await NotificationService(NotifyUOW(sessionmaker_)).dispatch(
        _email_request(user_ids)
    )

    assert await seed.count(NotificationDeliveryORM) == 70
    outbox = await seed.all(OutboxEventORM)
    assert len(outbox) == 2
    sizes = sorted(len(row.payload["delivery_ids"]) for row in outbox)
    assert sizes == [20, 50]


async def test_duplicate_request_is_idempotent(sessionmaker_, seed):
    user_ids = await seed.accounts(5)
    request = _email_request(user_ids)
    service = NotificationService(NotifyUOW(sessionmaker_))

    await service.dispatch(request)
    await NotificationService(NotifyUOW(sessionmaker_)).dispatch(request)

    assert await seed.count(NotificationORM) == 1
    assert await seed.count(NotificationDeliveryORM) == 5
    assert await seed.count(OutboxEventORM) == 1


async def test_retry_due_delivery_is_reenqueued(sessionmaker_, seed):
    (user_id,) = await seed.accounts(1)
    async with sessionmaker_() as session:
        notification = NotificationORM(
            event_id=uuid4(),
            category=NotificationCategory.system,
            title="t",
            body="b",
            data={},
        )
        session.add(notification)
        await session.flush()
        recipient = NotificationRecipientORM(
            notification_id=notification.id, user_id=user_id
        )
        session.add(recipient)
        await session.flush()
        session.add(
            NotificationDeliveryORM(
                notification_id=notification.id,
                recipient_id=recipient.id,
                user_id=user_id,
                transport=TransportTypeEnum.email,
                status=DeliveryStatus.retry_scheduled,
                attempts=1,
                max_attempts=5,
                next_attempt_at=datetime.now(timezone.utc)
                - timedelta(minutes=5),
            )
        )
        await session.commit()

    moved = await RetryReenqueueService(RetryUOW(sessionmaker_)).reenqueue_due()

    assert moved == 1
    deliveries = await seed.all(NotificationDeliveryORM)
    assert deliveries[0].status == DeliveryStatus.pending
    assert deliveries[0].next_attempt_at is None
    outbox = await seed.all(OutboxEventORM)
    assert len(outbox) == 1
    assert outbox[0].payload["delivery_ids"] == [str(deliveries[0].id)]
