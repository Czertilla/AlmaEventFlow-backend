from uuid import uuid4

from core.enum.notify import DeliveryStatus, TransportTypeEnum
from core.schema.message.notify import WebPushDeliveryBatch

from notify.models.client import ClientORM
from notify.models.delivery import NotificationDeliveryORM
from notify.models.notification import NotificationORM
from notify.models.recipient import NotificationRecipientORM
from notify.service.webpush import WebPushWorkerService
from notify.transport import registry
from notify.transport.webpush import WebPushDeliveryError
from notify.uow.delivery import WebPushDeliveryUOW


async def _seed_webpush(sessionmaker_, endpoints: list[str]):
    notification_id = uuid4()
    delivery_ids: list[uuid4] = []
    async with sessionmaker_() as session:
        session.add(
            NotificationORM(
                id=notification_id,
                event_id=uuid4(),
                category="system",
                title="t",
                body="b",
                data={},
            )
        )
        await session.flush()
        for endpoint in endpoints:
            user_id = uuid4()
            recipient = NotificationRecipientORM(
                notification_id=notification_id, user_id=user_id
            )
            session.add(recipient)
            await session.flush()
            client = ClientORM(
                user_id=user_id,
                transport=TransportTypeEnum.webpush,
                endpoint=endpoint,
                payload={"p256dh": "a", "auth": "b"},
                is_active=True,
            )
            session.add(client)
            await session.flush()
            delivery = NotificationDeliveryORM(
                notification_id=notification_id,
                recipient_id=recipient.id,
                user_id=user_id,
                transport=TransportTypeEnum.webpush,
                client_id=client.id,
                status=DeliveryStatus.pending,
                attempts=0,
                max_attempts=5,
            )
            session.add(delivery)
            await session.flush()
            delivery_ids.append(delivery.id)
        await session.commit()
    return notification_id, delivery_ids


async def test_batch_sends_once_and_writes_outcomes(
    sessionmaker_, seed, monkeypatch
):
    notification_id, delivery_ids = await _seed_webpush(
        sessionmaker_, ["ok-1", "ok-2", "dead-3"]
    )

    transport = registry.get(TransportTypeEnum.webpush)
    sent_endpoints: list[str] = []

    async def fake_push(client, content):
        sent_endpoints.append(client.endpoint)
        if client.endpoint.startswith("dead"):
            raise WebPushDeliveryError("gone", dead=True)

    monkeypatch.setattr(transport, "push", fake_push)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)

    assert sorted(sent_endpoints) == ["dead-3", "ok-1", "ok-2"]

    deliveries = {d.id: d for d in await seed.all(NotificationDeliveryORM)}
    statuses = {deliveries[d_id].status for d_id in delivery_ids}
    assert DeliveryStatus.sent in statuses
    assert DeliveryStatus.failed in statuses

    clients = {c.endpoint: c for c in await seed.all(ClientORM)}
    assert clients["dead-3"].is_active is False
    assert clients["ok-1"].is_active is True


async def test_terminal_deliveries_are_not_resent(sessionmaker_, seed, monkeypatch):
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, ["ok-1"])
    async with sessionmaker_() as session:
        delivery = await session.get(NotificationDeliveryORM, delivery_ids[0])
        delivery.status = DeliveryStatus.sent
        await session.commit()

    transport = registry.get(TransportTypeEnum.webpush)
    calls: list[str] = []

    async def fake_push(client, content):
        calls.append(client.endpoint)

    monkeypatch.setattr(transport, "push", fake_push)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)

    assert calls == []
