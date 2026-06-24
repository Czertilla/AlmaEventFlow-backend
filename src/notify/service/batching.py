from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from core.enum.notify import TransportTypeEnum

from notify.transport import registry
from notify.transport.base import DeliveryDraft

T = TypeVar("T")


@dataclass
class OutboxRow:
    """A transport batch ready to be written to the outbox."""

    topic: str
    payload: dict


def chunked(items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Yields consecutive slices of ``items`` of at most ``size`` elements."""
    step = max(size, 1)
    for start in range(0, len(items), step):
        yield items[start : start + step]


def build_outbox_rows(
    notification_id: UUID,
    drafts: dict[TransportTypeEnum, list[DeliveryDraft]],
) -> Iterable[OutboxRow]:
    """Groups drafts by transport and splits each group into batch messages of
    at most the transport's ``batch_size``. One ``OutboxRow`` becomes one Kafka
    message, regardless of how many deliveries it carries."""
    for transport_type, transport_drafts in drafts.items():
        if not transport_drafts:
            continue
        transport = registry.get(transport_type)
        if transport is None:
            continue
        for chunk in chunked(transport_drafts, transport.batch_size()):
            batch = transport.build_batch(notification_id, list(chunk))
            yield OutboxRow(
                topic=transport.delivery_topic,
                payload=batch.model_dump(mode="json"),
            )
