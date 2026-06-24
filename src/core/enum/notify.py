from enum import StrEnum, auto


class TransportTypeEnum(StrEnum):
    """Notification delivery transport. Shared by the notify service, producers
    and the frontend (via OpenAPI)."""

    email = auto()
    webpush = auto()
    telegram = auto()
    mobile = auto()
    realtime = auto()


class NotificationCategory(StrEnum):
    """Notification category, carried in ``NotificationRequest`` and usable for
    template selection and future per-category preferences."""

    general = auto()
    event = auto()
    attendance = auto()
    system = auto()


class DeliveryStatus(StrEnum):
    """Lifecycle of a single ``notification_delivery`` row.

    ``pending`` — created, awaiting publication/handling. ``retry_scheduled`` —
    temporary error, eligible for another attempt. Terminal states never
    transition further: ``sent`` (handed to provider), ``delivered``
    (provider-confirmed), ``failed`` (permanent error), ``skipped`` (inactive
    endpoint / suppressed), ``expired`` (past ``expires_at``), ``cancelled``."""

    pending = auto()
    retry_scheduled = auto()
    sent = auto()
    delivered = auto()
    failed = auto()
    skipped = auto()
    expired = auto()
    cancelled = auto()

    @classmethod
    def terminal(cls) -> frozenset["DeliveryStatus"]:
        """Statuses a delivery never leaves; consumers skip these on redelivery."""
        return frozenset(
            {
                cls.sent,
                cls.delivered,
                cls.failed,
                cls.skipped,
                cls.expired,
                cls.cancelled,
            }
        )


class OutboxStatus(StrEnum):
    """Lifecycle of an ``outbox_event`` row processed by the outbox publisher."""

    pending = auto()
    published = auto()
    failed = auto()
