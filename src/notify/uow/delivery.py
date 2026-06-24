from core.uow.sqlalchemy import UnitOfWork

from notify.repository.delivery import NotificationDeliveryRepo
from notify.uow.client import ClientMixin
from notify.uow.notification import NotificationMixin


class DeliveryMixin:
    deliveries: NotificationDeliveryRepo


class WebPushDeliveryUOW(
    UnitOfWork, DeliveryMixin, NotificationMixin, ClientMixin
):
    """Used by the in-notify web push worker: delivery + notification content +
    endpoint, plus direct status writes."""


class DeliveryResultUOW(UnitOfWork, DeliveryMixin, ClientMixin):
    """Used by the result consumer to apply outcomes reported by external
    workers and deactivate dead endpoints."""
