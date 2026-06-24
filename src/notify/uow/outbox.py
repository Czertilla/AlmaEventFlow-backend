from core.uow.sqlalchemy import UnitOfWork

from notify.repository.outbox import OutboxRepo
from notify.uow.account import AccountMixin
from notify.uow.client import ClientMixin
from notify.uow.delivery import DeliveryMixin
from notify.uow.notification import NotificationMixin


class OutboxMixin:
    outbox: OutboxRepo


class OutboxUOW(UnitOfWork, OutboxMixin, DeliveryMixin):
    """Used by the outbox publisher to drain pending rows and publish them."""


class RetryUOW(
    UnitOfWork,
    DeliveryMixin,
    NotificationMixin,
    AccountMixin,
    ClientMixin,
    OutboxMixin,
):
    """Used by the retry worker to rebuild batches for deliveries whose backoff
    has elapsed and re-enqueue them through the outbox."""
