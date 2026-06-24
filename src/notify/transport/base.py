from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from core.enum.notify import TransportTypeEnum
from core.schema.message.core import MQRequest

from notify.schema.account import AccountRead
from notify.schema.client import ClientTarget
from notify.schema.notification import NotificationContent


@dataclass
class PlanContext:
    """Per-recipient data the ingest service hands to a transport to build a
    delivery task."""

    notification_id: UUID
    user_id: UUID
    content: NotificationContent
    account: AccountRead | None
    expires_at: datetime | None


@dataclass
class DeliveryTarget:
    """A single endpoint to deliver to. ``client`` is ``None`` for recipient-
    addressed transports (e.g. email resolves the address from the account)."""

    client: ClientTarget | None = None


@dataclass
class DeliveryDraft:
    """A persisted delivery awaiting publication, carrying the context needed to
    build its slot in a transport batch."""

    delivery_id: UUID
    ctx: PlanContext
    target: DeliveryTarget


class BaseTransport(ABC):
    """Transport plugin and extension point. A transport contributes metadata,
    a delivery topic, a batch size and a batch builder; it never performs
    delivery inline. Subclass ``DelegatedTransport`` or ``DirectTransport`` and
    register the instance in ``notify.transport.registry``."""

    type: ClassVar[TransportTypeEnum]
    label: ClassVar[str]
    delivery_topic: ClassVar[str]
    delegated: ClassVar[bool] = False
    requires_client: ClassVar[bool] = True

    def is_available(self) -> bool:
        return True

    def batch_size(self) -> int:
        """Maximum deliveries per transport batch message. ``1`` keeps strict
        per-delivery publication while staying batch-compatible."""
        return 1

    def validate_client_payload(self, payload: dict[str, str]) -> dict[str, str]:
        return payload

    @abstractmethod
    def build_batch(
        self, notification_id: UUID, drafts: list[DeliveryDraft]
    ) -> MQRequest:
        """Builds the single message published to ``delivery_topic`` for a chunk
        of deliveries of this transport."""
        raise NotImplementedError


class DelegatedTransport(BaseTransport):
    """Delivery delegated to a downstream microservice via a delivery topic."""

    delegated = True
    requires_client = False


class DirectTransport(BaseTransport):
    """notify performs the delivery protocol itself against client endpoints."""

    delegated = False
    requires_client = True
