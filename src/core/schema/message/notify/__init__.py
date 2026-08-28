from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import EmailStr, Field, model_validator

from core.enum.notify import (
    DeliveryStatus,
    NotificationCategory,
    TransportTypeEnum,
)
from core.schema.message.core import MQRequest


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NotificationRequest(MQRequest):
    """Inbound notification contract (``NotifyQueue.SEND``). ``event_id`` is the
    idempotency key: re-publishing the same id is a no-op. Recipients are given
    as ``user_ids`` and/or ``person_ids`` (the latter resolved to users via the
    account projection); at least one must be non-empty. ``transports``
    optionally restricts the set of transports for this notification."""

    event_id: UUID = Field(default_factory=uuid4)
    user_ids: list[UUID] = Field(default_factory=list)
    person_ids: list[UUID] = Field(default_factory=list)
    category: NotificationCategory = NotificationCategory.general
    title: str
    body: str = ""
    action_url: str | None = None
    data: dict[str, str] = Field(default_factory=dict)
    transports: list[TransportTypeEnum] | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def _require_recipients(self) -> "NotificationRequest":
        if not self.user_ids and not self.person_ids:
            raise ValueError("user_ids or person_ids must be provided")
        return self


class TransportBatch(MQRequest):
    """Technical transport dispatch message: a group of deliveries of one
    transport, published as a single Kafka message. It is decoupled from
    ``notification_delivery`` — one batch carries many atomic deliveries.
    ``delivery_ids`` is the canonical batch membership list."""

    message_id: UUID = Field(default_factory=uuid4)
    notification_id: UUID
    transport: TransportTypeEnum
    delivery_ids: list[UUID] = Field(min_length=1)
    created_at: datetime = Field(default_factory=_utcnow)


class EmailDeliveryItem(MQRequest):
    """Inline per-delivery content for an email batch. Lets the ``mail`` service
    render and send without loading anything from the notify database, while
    keeping the result attributable to a single ``delivery_id``."""

    delivery_id: UUID
    recipient: EmailStr
    subject: str
    template: str
    context: dict[str, str] = Field(default_factory=dict)
    expires_at: datetime | None = None


class EmailDeliveryBatch(TransportBatch):
    """Email transport batch (``NotifyDeliveryQueue.EMAIL``)."""

    items: list[EmailDeliveryItem] = Field(min_length=1)


class WebPushDeliveryBatch(TransportBatch):
    """Web push transport batch (``NotifyDeliveryQueue.WEBPUSH``). Carries only
    ids; the in-notify worker loads delivery, notification and endpoint from the
    shared database."""


class TelegramButton(MQRequest):
    """One inline keyboard button. ``callback_data`` is opaque to notify — the
    ``bot`` service defines and interprets its own callback formats."""

    text: str
    callback_data: str


class TelegramDeliveryItem(MQRequest):
    """Inline per-delivery content for a Telegram batch. Self-contained (like
    ``EmailDeliveryItem``) since ``bot`` doesn't share notify's database.
    ``correlation_key`` (the domain id the notification is about, e.g. an
    event id) lets ``bot`` decide whether to edit a previously-sent message
    instead of sending a new one."""

    delivery_id: UUID
    chat_id: str
    text: str
    buttons: list[list[TelegramButton]] = Field(default_factory=list)
    correlation_key: str | None = None
    message_thread_id: int | None = None
    """Forum-topic id, for chats organized into topics. Only meaningful when
    sending a new message — an edit targets an existing message_id, whose
    topic is already fixed."""
    expires_at: datetime | None = None


class TelegramDeliveryBatch(TransportBatch):
    """Telegram transport batch (``NotifyDeliveryQueue.TELEGRAM``)."""

    items: list[TelegramDeliveryItem] = Field(min_length=1)


class DeliveryResult(MQRequest):
    """Delivery outcome reported by an external worker (``RESULT`` topic). One
    result updates exactly one ``notification_delivery``."""

    delivery_id: UUID
    status: DeliveryStatus
    error: str | None = None
    provider_message_id: str | None = None


class RegisterClientRequest(MQRequest):
    user_id: UUID
    transport: TransportTypeEnum = TransportTypeEnum.webpush
    endpoint: str
    label: str | None = None
    payload: dict[str, str] = Field(default_factory=dict)


class ClientData(MQRequest):
    id: UUID
    transport: TransportTypeEnum
    endpoint: str
    label: str | None = None
    is_active: bool
    created_at: datetime


class DeregisterClientRequest(MQRequest):
    user_id: UUID
    client_id: UUID


class GetPreferencesRequest(MQRequest):
    user_id: UUID


class PreferenceItemData(MQRequest):
    transport: TransportTypeEnum
    is_enabled: bool


class PreferencesData(MQRequest):
    preferences: list[PreferenceItemData]


class SetPreferencesRequest(MQRequest):
    user_id: UUID
    preferences: list[PreferenceItemData] = Field(min_length=1)
