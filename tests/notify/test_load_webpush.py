import asyncio
import logging
import time
from dataclasses import dataclass, field
from statistics import median
from uuid import UUID, uuid4

import pytest

logger = logging.getLogger(__name__)

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

pytestmark = pytest.mark.load


@dataclass
class LoadTestStats:
    name: str = ""
    count: int = 0
    page_size: int = 200
    concurrency_limit: int = 50
    simulated_delay: float = 0.0
    elapsed: float = 0.0
    db_seed_elapsed: float = 0.0
    db_read_elapsed: float = 0.0
    send_latencies: list[float] = field(default_factory=list)
    concurrency_peak: int = 0
    outcomes: dict[DeliveryStatus, int] = field(default_factory=dict)
    pages_processed: int = 0
    send_calls: int = 0
    transport_unavailable: bool = False
    notification_expired: bool = False

    def record_send(self, duration: float):
        self.send_latencies.append(duration)
        self.send_calls += 1

    @property
    def throughput(self) -> float:
        if self.elapsed == 0:
            return 0.0
        return self.count / self.elapsed

    @property
    def p50(self) -> float:
        if not self.send_latencies:
            return 0.0
        return median(self.send_latencies)

    @property
    def p90(self) -> float:
        if not self.send_latencies:
            return 0.0
        s = sorted(self.send_latencies)
        return s[int(len(s) * 0.9)]

    @property
    def p99(self) -> float:
        if not self.send_latencies:
            return 0.0
        s = sorted(self.send_latencies)
        return s[int(len(s) * 0.99)]

    @property
    def avg_send(self) -> float:
        if not self.send_latencies:
            return 0.0
        return sum(self.send_latencies) / len(self.send_latencies)

    def print(self):
        sep = "─" * 88
        lines = [
            "",
            sep,
            f"  LoadTestStats ── {self.name}",
            sep,
            f"  Configuration:",
            f"    deliveries          : {self.count}",
            f"    page_size           : {self.page_size}",
            f"    concurrency_limit   : {self.concurrency_limit}",
            f"    simulated_delay     : {self.simulated_delay*1000:.1f}ms" if self.simulated_delay else f"    simulated_delay     : none",
            f"  Timing:",
            f"    total elapsed       : {self.elapsed:.4f}s",
            f"    db seed             : {self.db_seed_elapsed:.4f}s",
            f"    db read             : {self.db_read_elapsed:.4f}s",
            f"  Throughput:",
            f"    deliveries/sec      : {self.throughput:.1f}",
        ]
        if self.send_calls:
            lines.append(f"    sends/sec           : {self.send_calls / self.elapsed:.1f}" if self.elapsed else "")
        lines += [
            f"  Send Latency:",
            f"    avg                 : {self.avg_send*1000:.3f}ms",
            f"    p50                 : {self.p50*1000:.3f}ms",
            f"    p90                 : {self.p90*1000:.3f}ms",
            f"    p99                 : {self.p99*1000:.3f}ms",
            f"  Concurrency:",
            f"    peak concurrent     : {self.concurrency_peak}",
        ]
        if self.concurrency_limit:
            lines.append(f"    efficiency          : {self.concurrency_peak / self.concurrency_limit * 100:.1f}%")
        lines.append(f"  Outcomes:")
        if self.transport_unavailable:
            lines.append(f"    transport_unavailable: true")
            lines.append(f"    retry_scheduled     : {self.outcomes.get(DeliveryStatus.retry_scheduled, 0)}")
        elif self.notification_expired:
            lines.append(f"    notification_expired : true")
            lines.append(f"    expired             : {self.outcomes.get(DeliveryStatus.expired, 0)}")
        else:
            for status in (DeliveryStatus.sent, DeliveryStatus.failed,
                           DeliveryStatus.skipped, DeliveryStatus.retry_scheduled):
                val = self.outcomes.get(status, 0)
                if val:
                    pct = val / self.count * 100
                    lines.append(f"    {status.value:<20}: {val:>5} ({pct:5.1f}%)")
        lines += [
            f"  Pages:",
            f"    pages_processed     : {self.pages_processed}",
        ]
        if self.pages_processed:
            lines.append(f"    avg page time       : {self.elapsed / self.pages_processed:.4f}s")
        lines += [sep, ""]
        logger.info("\n".join(lines))


async def _seed_webpush(sessionmaker_, endpoints: list[str]):
    notification_id = uuid4()
    delivery_ids: list[UUID] = []
    async with sessionmaker_() as session:
        session.add(
            NotificationORM(
                id=notification_id,
                event_id=uuid4(),
                category="system",
                title="Load Test",
                body="Load test notification body",
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


async def _read_outcomes(sessionmaker_, delivery_ids: list[UUID]) -> dict[DeliveryStatus, int]:
    outcomes: dict[DeliveryStatus, int] = {}
    async with sessionmaker_() as session:
        from sqlalchemy import select, func

        rows = await session.execute(
            select(NotificationDeliveryORM.status, func.count())
            .where(NotificationDeliveryORM.id.in_(delivery_ids))
            .group_by(NotificationDeliveryORM.status)
        )
        for status, count in rows:
            outcomes[status] = count
    return outcomes


@pytest.mark.parametrize("count", [50, 200, 500])
async def test_throughput_scales_with_batch_size(
    sessionmaker_, seed, monkeypatch, count
):
    stats = LoadTestStats(name="throughput_scales_with_batch_size", count=count)

    t_seed = time.perf_counter()
    endpoints = [f"https://push.example.com/{i}" for i in range(count)]
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, endpoints)
    stats.db_seed_elapsed = time.perf_counter() - t_seed

    transport = registry.get(TransportTypeEnum.webpush)
    sent = []

    async def fake_send(session, client, content):
        sent.append(client.endpoint)

    monkeypatch.setattr(transport, "send", fake_send)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )

    t0 = time.perf_counter()
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)
    stats.elapsed = time.perf_counter() - t0

    t_read = time.perf_counter()
    stats.outcomes = await _read_outcomes(sessionmaker_, delivery_ids)
    stats.db_read_elapsed = time.perf_counter() - t_read
    stats.send_calls = len(sent)

    assert len(sent) == count
    deliveries = {d.id: d for d in await seed.all(NotificationDeliveryORM)}
    assert all(deliveries[d_id].status == DeliveryStatus.sent for d_id in delivery_ids)

    stats.print()


async def test_concurrent_fan_out(
    sessionmaker_, seed, monkeypatch
):
    count = 200
    delay = 0.01
    stats = LoadTestStats(
        name="concurrent_fan_out", count=count, simulated_delay=delay
    )

    t_seed = time.perf_counter()
    endpoints = [f"https://push.example.com/{i}" for i in range(count)]
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, endpoints)
    stats.db_seed_elapsed = time.perf_counter() - t_seed

    transport = registry.get(TransportTypeEnum.webpush)
    send_latencies = []
    lock = asyncio.Lock()

    async def fake_send(session, client, content):
        t0 = time.perf_counter()
        await asyncio.sleep(delay)
        async with lock:
            send_latencies.append(time.perf_counter() - t0)

    monkeypatch.setattr(transport, "send", fake_send)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )

    t0 = time.perf_counter()
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)
    stats.elapsed = time.perf_counter() - t0

    stats.send_latencies = send_latencies
    stats.send_calls = len(send_latencies)

    t_read = time.perf_counter()
    stats.outcomes = await _read_outcomes(sessionmaker_, delivery_ids)
    stats.db_read_elapsed = time.perf_counter() - t_read

    expected_serial = count * delay
    assert stats.elapsed < expected_serial, (
        f"Total time {stats.elapsed:.2f}s exceeds serial estimate {expected_serial:.2f}s"
    )

    stats.print()


@pytest.mark.parametrize("dead_ratio", [0.0, 0.1, 0.5, 0.9])
async def test_mixed_outcomes_under_load(
    sessionmaker_, seed, monkeypatch, dead_ratio
):
    count = 200
    stats = LoadTestStats(
        name=f"mixed_outcomes_under_load (dead_ratio={dead_ratio})",
        count=count,
    )

    t_seed = time.perf_counter()
    endpoints = [f"https://push.example.com/{i}" for i in range(count)]
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, endpoints)
    stats.db_seed_elapsed = time.perf_counter() - t_seed

    transport = registry.get(TransportTypeEnum.webpush)
    sent_endpoints = []
    send_latencies = []

    async def fake_send(session, client, content):
        t0 = time.perf_counter()
        idx = int(client.endpoint.rsplit("/", 1)[-1])
        if idx < count * dead_ratio:
            raise WebPushDeliveryError("gone", dead=True)
        sent_endpoints.append(client.endpoint)
        send_latencies.append(time.perf_counter() - t0)

    monkeypatch.setattr(transport, "send", fake_send)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )

    t0 = time.perf_counter()
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)
    stats.elapsed = time.perf_counter() - t0

    stats.send_latencies = send_latencies
    stats.send_calls = len(send_latencies)

    t_read = time.perf_counter()
    stats.outcomes = await _read_outcomes(sessionmaker_, delivery_ids)
    stats.db_read_elapsed = time.perf_counter() - t_read

    deliveries = {d.id: d for d in await seed.all(NotificationDeliveryORM)}
    statuses = {deliveries[d_id].status for d_id in delivery_ids}
    if dead_ratio > 0:
        assert DeliveryStatus.failed in statuses
    if dead_ratio < 1.0:
        assert DeliveryStatus.sent in statuses

    stats.print()


async def test_concurrency_limit_respected(
    sessionmaker_, seed, monkeypatch
):
    count = 500
    concurrency_limit = 50
    stats = LoadTestStats(
        name="concurrency_limit_respected",
        count=count,
        concurrency_limit=concurrency_limit,
    )

    from notify.config.settings import settings

    monkeypatch.setattr(settings, "WEBPUSH_SEND_CONCURRENCY", concurrency_limit)

    t_seed = time.perf_counter()
    endpoints = [f"https://push.example.com/{i}" for i in range(count)]
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, endpoints)
    stats.db_seed_elapsed = time.perf_counter() - t_seed

    transport = registry.get(TransportTypeEnum.webpush)
    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()
    send_latencies = []

    async def fake_send(session, client, content):
        nonlocal in_flight, max_in_flight, send_latencies
        t0 = time.perf_counter()
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.005)
        async with lock:
            in_flight -= 1
        send_latencies.append(time.perf_counter() - t0)

    monkeypatch.setattr(transport, "send", fake_send)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )

    t0 = time.perf_counter()
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)
    stats.elapsed = time.perf_counter() - t0

    stats.send_latencies = send_latencies
    stats.send_calls = len(send_latencies)
    stats.concurrency_peak = max_in_flight

    t_read = time.perf_counter()
    stats.outcomes = await _read_outcomes(sessionmaker_, delivery_ids)
    stats.db_read_elapsed = time.perf_counter() - t_read

    assert stats.concurrency_peak <= concurrency_limit, (
        f"Concurrency exceeded: peak={stats.concurrency_peak} > limit={concurrency_limit}"
    )

    stats.print()


async def test_inactive_clients_skipped_under_load(
    sessionmaker_, seed, monkeypatch
):
    count = 100
    stats = LoadTestStats(name="inactive_clients_skipped_under_load", count=count)

    t_seed = time.perf_counter()
    endpoints = [f"https://push.example.com/{i}" for i in range(count)]
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, endpoints)

    async with sessionmaker_() as session:
        from sqlalchemy import select

        result = await session.execute(select(ClientORM).limit(count // 2))
        for client in result.scalars():
            client.is_active = False
        await session.commit()
    stats.db_seed_elapsed = time.perf_counter() - t_seed

    transport = registry.get(TransportTypeEnum.webpush)
    send_latencies = []

    async def fake_send(session, client, content):
        t0 = time.perf_counter()
        send_latencies.append(time.perf_counter() - t0)

    monkeypatch.setattr(transport, "send", fake_send)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )

    t0 = time.perf_counter()
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)
    stats.elapsed = time.perf_counter() - t0

    stats.send_latencies = send_latencies
    stats.send_calls = len(send_latencies)

    t_read = time.perf_counter()
    stats.outcomes = await _read_outcomes(sessionmaker_, delivery_ids)
    stats.db_read_elapsed = time.perf_counter() - t_read

    assert stats.outcomes.get(DeliveryStatus.sent, 0) == count // 2
    assert stats.outcomes.get(DeliveryStatus.skipped, 0) == count // 2

    stats.print()


async def test_page_by_page_processing(
    sessionmaker_, seed, monkeypatch
):
    count = 300
    page_size = 50
    stats = LoadTestStats(
        name="page_by_page_processing",
        count=count,
        page_size=page_size,
    )

    from notify.config.settings import settings

    monkeypatch.setattr(settings, "WEBPUSH_LOAD_PAGE_SIZE", page_size)

    t_seed = time.perf_counter()
    endpoints = [f"https://push.example.com/{i}" for i in range(count)]
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, endpoints)
    stats.db_seed_elapsed = time.perf_counter() - t_seed

    transport = registry.get(TransportTypeEnum.webpush)
    send_latencies = []

    async def fake_send(session, client, content):
        t0 = time.perf_counter()
        send_latencies.append(time.perf_counter() - t0)

    monkeypatch.setattr(transport, "send", fake_send)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )

    t0 = time.perf_counter()
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)
    stats.elapsed = time.perf_counter() - t0

    expected_pages = (count + page_size - 1) // page_size
    stats.pages_processed = expected_pages

    stats.send_latencies = send_latencies
    stats.send_calls = len(send_latencies)

    t_read = time.perf_counter()
    stats.outcomes = await _read_outcomes(sessionmaker_, delivery_ids)
    stats.db_read_elapsed = time.perf_counter() - t_read

    stats.print()


async def test_transient_failures_scheduled_for_retry(
    sessionmaker_, seed, monkeypatch
):
    count = 99
    stats = LoadTestStats(
        name="transient_failures_retry", count=count
    )

    t_seed = time.perf_counter()
    endpoints = [f"https://push.example.com/{i}" for i in range(count)]
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, endpoints)
    stats.db_seed_elapsed = time.perf_counter() - t_seed

    transport = registry.get(TransportTypeEnum.webpush)
    send_latencies = []

    async def fake_send(session, client, content):
        t0 = time.perf_counter()
        idx = int(client.endpoint.rsplit("/", 1)[-1])
        if idx % 3 == 0:
            raise WebPushDeliveryError("timeout", dead=False)
        if idx % 3 == 1:
            raise WebPushDeliveryError("gone", dead=True)
        send_latencies.append(time.perf_counter() - t0)

    monkeypatch.setattr(transport, "send", fake_send)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )

    t0 = time.perf_counter()
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)
    stats.elapsed = time.perf_counter() - t0

    stats.send_latencies = send_latencies
    stats.send_calls = len(send_latencies)

    t_read = time.perf_counter()
    stats.outcomes = await _read_outcomes(sessionmaker_, delivery_ids)
    stats.db_read_elapsed = time.perf_counter() - t_read

    assert DeliveryStatus.sent in stats.outcomes
    assert DeliveryStatus.failed in stats.outcomes
    assert DeliveryStatus.retry_scheduled in stats.outcomes

    stats.print()


async def test_expired_notification_terminates_all(
    sessionmaker_, seed, monkeypatch
):
    count = 100
    stats = LoadTestStats(
        name="expired_notification_terminates_all",
        count=count,
        notification_expired=True,
    )

    t_seed = time.perf_counter()
    endpoints = [f"https://push.example.com/{i}" for i in range(count)]
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, endpoints)

    from datetime import datetime, timezone, timedelta

    async with sessionmaker_() as session:
        notification = await session.get(NotificationORM, notification_id)
        notification.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await session.commit()
    stats.db_seed_elapsed = time.perf_counter() - t_seed

    transport = registry.get(TransportTypeEnum.webpush)
    monkeypatch.setattr(transport, "is_available", lambda: True)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )

    t0 = time.perf_counter()
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)
    stats.elapsed = time.perf_counter() - t0

    t_read = time.perf_counter()
    stats.outcomes = await _read_outcomes(sessionmaker_, delivery_ids)
    stats.db_read_elapsed = time.perf_counter() - t_read

    assert stats.outcomes.get(DeliveryStatus.expired, 0) == count

    stats.print()


async def test_transport_unavailable_reschedules(
    sessionmaker_, seed, monkeypatch
):
    count = 50
    stats = LoadTestStats(
        name="transport_unavailable_reschedules",
        count=count,
        transport_unavailable=True,
    )

    t_seed = time.perf_counter()
    endpoints = [f"https://push.example.com/{i}" for i in range(count)]
    notification_id, delivery_ids = await _seed_webpush(sessionmaker_, endpoints)
    stats.db_seed_elapsed = time.perf_counter() - t_seed

    transport = registry.get(TransportTypeEnum.webpush)
    monkeypatch.setattr(transport, "is_available", lambda: False)

    batch = WebPushDeliveryBatch(
        notification_id=notification_id,
        transport=TransportTypeEnum.webpush,
        delivery_ids=delivery_ids,
    )

    t0 = time.perf_counter()
    await WebPushWorkerService(WebPushDeliveryUOW(sessionmaker_)).handle(batch)
    stats.elapsed = time.perf_counter() - t0

    t_read = time.perf_counter()
    stats.outcomes = await _read_outcomes(sessionmaker_, delivery_ids)
    stats.db_read_elapsed = time.perf_counter() - t_read

    assert stats.outcomes.get(DeliveryStatus.retry_scheduled, 0) == count

    stats.print()
