"""Real request/reply over Kafka.

FastStream's aiokafka producer never implements ``request()`` outside the
test client -- ``AioKafkaFastProducer.request()`` always raises
``FeatureNotSupportedException`` (unlike RabbitMQ, Kafka has no broker-native
reply-queue concept). The *subscriber* side is already reply-capable though:
whenever an incoming message carries a ``reply_to`` header, the handler's
return value is published straight to that topic with the same
``correlation_id`` (see ``faststream.kafka.subscriber.usecase.KafkaFakePublisher``
and ``_internal.endpoint.subscriber.usecase`` line ~372). Only the requesting
side was missing.

This fills that gap the same way FastStream's own RabbitMQ producer does it:
publish with ``reply_to`` pointed at one shared topic, and demux replies by
``correlation_id`` from a background consumer on it. Kafka has no
per-connection exclusive queue like RabbitMQ's ``amq.rabbitmq.reply-to``, so
instance isolation instead comes from each broker instance consuming that
topic under its own randomly generated (and therefore always-fresh, never
replaying old replies) consumer group -- every reply is broadcast to every
listening instance, and each just ignores correlation_ids it isn't waiting
on.

Requires the ``core.rpc.reply`` topic to exist (or auto-creation enabled),
same as any other topic this app publishes to.
"""

import asyncio
import contextlib
from logging import getLogger
from typing import TYPE_CHECKING, Any, Self, override
from uuid import uuid4

from aiokafka import AIOKafkaConsumer
from faststream.kafka.publisher.producer import AioKafkaFastProducerImpl

if TYPE_CHECKING:
    from faststream._internal.configs.broker import ConfigComposition
    from faststream.kafka.configs.broker import KafkaBrokerConfig
    from faststream.kafka.response import KafkaPublishCommand

logger = getLogger(__name__)

REPLY_TOPIC = "core.rpc.reply"


def _slot_names(cls: type) -> list[str]:
    return [
        slot
        for klass in cls.__mro__
        for slot in getattr(klass, "__slots__", ())
        if slot not in ("__dict__", "__weakref__")
    ]


class KafkaRpcProducer(AioKafkaFastProducerImpl):
    """FastStream's slotted producer with a working ``request()``. The
    producer cannot be patched in place (its instances have no ``__dict__``),
    so the broker's own instance is replaced by this subclass carrying the
    same state -- everything else about it (publish, connect, codec,
    serializer) is inherited untouched."""

    _reply: "KafkaRpcReplyConsumer"

    @classmethod
    def adopt(
        cls,
        producer: AioKafkaFastProducerImpl,
        reply: "KafkaRpcReplyConsumer",
    ) -> Self:
        adopted = cls.__new__(cls)
        for slot in _slot_names(AioKafkaFastProducerImpl):
            setattr(adopted, slot, getattr(producer, slot))
        adopted._reply = reply
        return adopted

    @override
    async def request(self, cmd: "KafkaPublishCommand") -> Any:
        return await self._reply.request(self, cmd)


class KafkaRpcReplyConsumer:
    """Owns the background reply consumer and pending-request table for one
    broker instance. ``attach()`` makes the broker's producer route
    ``request()`` through it. The consumer itself is
    started lazily on the first actual request, so services that only
    publish/subscribe never pay for an extra topic subscription."""

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        client_id: str,
        connect_kwargs: dict[str, Any],
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._connect_kwargs = connect_kwargs
        self._pending: dict[str, asyncio.Future[Any]] = {}
        self._consumer: AIOKafkaConsumer | None = None
        self._consume_task: asyncio.Task | None = None
        self._start_lock = asyncio.Lock()

    async def _ensure_started(self) -> None:
        if self._consumer is not None:
            return
        async with self._start_lock:
            if self._consumer is not None:
                return
            consumer = AIOKafkaConsumer(
                REPLY_TOPIC,
                bootstrap_servers=self._bootstrap_servers,
                group_id=f"rpc-reply-{uuid4().hex}",
                client_id=f"{self._client_id}-rpc-reply",
                auto_offset_reset="latest",
                enable_auto_commit=True,
                **self._connect_kwargs,
            )
            await consumer.start()
            self._consumer = consumer
            self._consume_task = asyncio.create_task(self._consume_loop())
            logger.info("Kafka RPC reply consumer started on topic=%s", REPLY_TOPIC)

    async def stop(self) -> None:
        if self._consume_task is not None:
            self._consume_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consume_task
            self._consume_task = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def _consume_loop(self) -> None:
        assert self._consumer is not None
        async for record in self._consumer:
            headers = dict(record.headers or ())
            correlation_id = (headers.get("correlation_id") or b"").decode()
            future = self._pending.pop(correlation_id, None)
            if future is not None and not future.done():
                future.set_result(record)

    async def request(
        self, producer: AioKafkaFastProducerImpl, cmd: "KafkaPublishCommand"
    ) -> Any:
        await self._ensure_started()
        cmd.reply_to = REPLY_TOPIC
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[cmd.correlation_id] = future
        try:
            await producer.publish(cmd)
            return await asyncio.wait_for(future, timeout=cmd.timeout)
        finally:
            self._pending.pop(cmd.correlation_id, None)

    def attach(self, config: "ConfigComposition[KafkaBrokerConfig]") -> None:
        broker_config = config.broker_config
        producer = broker_config.producer
        if not isinstance(producer, AioKafkaFastProducerImpl):
            raise TypeError(
                f"cannot add request/reply to {type(producer).__name__}"
            )
        broker_config.producer = KafkaRpcProducer.adopt(producer, self)
