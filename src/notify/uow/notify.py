from core.uow.sqlalchemy import UnitOfWork
from notify.uow.account import AccountMixin
from notify.uow.client import ClientMixin
from notify.uow.delivery import DeliveryMixin
from notify.uow.notification import NotificationMixin
from notify.uow.outbox import OutboxMixin
from notify.uow.preference import PreferenceMixin
from notify.uow.recipient import RecipientMixin


class NotifyUOW(
    UnitOfWork,
    AccountMixin,
    PreferenceMixin,
    ClientMixin,
    NotificationMixin,
    RecipientMixin,
    DeliveryMixin,
    OutboxMixin,
):
    """Ingest UOW: resolves recipients (accounts, preferences, clients) and
    persists the notification, deliveries and outbox rows in one transaction."""
