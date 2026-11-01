from profile.repository.outbox import NotificationOutboxRepo
from profile.repository.visibility import VisibilityHistoryRepo, VisibilityRepo
from profile.uow.account import AccountMixin
from profile.uow.organization import OrganizationMixin
from profile.uow.person import PersonMixin

from core.uow.sqlalchemy import UnitOfWork


class VisibilityMixin:
    visibility: VisibilityRepo


class VisibilityHistoryMixin:
    visibility_history: VisibilityHistoryRepo


class OutboxMixin:
    notification_outbox: NotificationOutboxRepo


class VisibilityUOW(
    UnitOfWork,
    VisibilityMixin,
    VisibilityHistoryMixin,
    OutboxMixin,
    AccountMixin,
    OrganizationMixin,
    PersonMixin,
): ...


class OutboxUOW(UnitOfWork, OutboxMixin): ...
