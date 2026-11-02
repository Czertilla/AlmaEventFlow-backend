from profile.repository.outbox import NotificationOutboxRepo

from core.uow.sqlalchemy import UnitOfWork


class OutboxMixin:
    notification_outbox: NotificationOutboxRepo


class OutboxUOW(UnitOfWork, OutboxMixin): ...
