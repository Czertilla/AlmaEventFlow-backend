import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from faststream.kafka import KafkaBroker

from core.broker.kafka_rpc import (
    REPLY_TOPIC,
    KafkaRpcProducer,
    KafkaRpcReplyConsumer,
)


def _consumer() -> KafkaRpcReplyConsumer:
    return KafkaRpcReplyConsumer(
        bootstrap_servers="localhost:9092", client_id="test", connect_kwargs={}
    )


def test_attaching_swaps_the_slotted_producer_for_one_that_can_request() -> None:
    broker = KafkaBroker("localhost:9092")
    original = broker.config.producer
    reply = _consumer()

    reply.attach(broker.config)

    swapped = broker.config.producer
    assert isinstance(swapped, KafkaRpcProducer)
    assert swapped is not original
    for slot in ("_parser", "_decoder", "_producer", "serializer", "codec"):
        assert getattr(swapped, slot) is getattr(original, slot)


def test_the_swapped_producer_sends_requests_through_the_reply_consumer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = KafkaBroker("localhost:9092")
    reply = _consumer()
    reply.attach(broker.config)
    seen: list[Any] = []

    async def record(producer: Any, cmd: Any) -> str:
        seen.append((producer, cmd))
        return "answer"

    monkeypatch.setattr(reply, "request", record)
    command = SimpleNamespace(correlation_id="c1")

    answer = asyncio.run(broker.config.producer.request(command))  # pyright: ignore[reportArgumentType]

    assert answer == "answer"
    assert seen == [(broker.config.producer, command)]


def test_a_producer_that_cannot_be_adopted_is_refused() -> None:
    config = SimpleNamespace(broker_config=SimpleNamespace(producer=object()))

    with pytest.raises(TypeError, match="request/reply"):
        _consumer().attach(config)  # pyright: ignore[reportArgumentType]


class _Producer:
    def __init__(self, answer: Any = None) -> None:
        self.answer = answer
        self.published: list[Any] = []
        self.consumer: KafkaRpcReplyConsumer | None = None

    async def publish(self, cmd: Any) -> None:
        self.published.append(cmd)
        if self.answer is not None and self.consumer is not None:
            self.consumer._pending[cmd.correlation_id].set_result(self.answer)  # pyright: ignore[reportPrivateUsage]


async def test_a_request_goes_to_the_reply_topic_and_resolves_on_its_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reply = _consumer()

    async def started() -> None:
        return None

    monkeypatch.setattr(reply, "_ensure_started", started)
    producer = _Producer(answer="reply-record")
    producer.consumer = reply
    command = SimpleNamespace(correlation_id="c1", timeout=1.0, reply_to=None)

    answer = await reply.request(producer, command)  # pyright: ignore[reportArgumentType]

    assert answer == "reply-record"
    assert command.reply_to == REPLY_TOPIC
    assert producer.published == [command]
    assert reply._pending == {}  # pyright: ignore[reportPrivateUsage]


async def test_a_request_nobody_answers_times_out_and_leaves_nothing_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reply = _consumer()

    async def started() -> None:
        return None

    monkeypatch.setattr(reply, "_ensure_started", started)
    command = SimpleNamespace(correlation_id="c2", timeout=0.05, reply_to=None)

    with pytest.raises(TimeoutError):
        await reply.request(_Producer(), command)  # pyright: ignore[reportArgumentType]

    assert reply._pending == {}  # pyright: ignore[reportPrivateUsage]
