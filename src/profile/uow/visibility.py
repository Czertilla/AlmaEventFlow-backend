from profile.repository.visibility import VisibilityHistoryRepo, VisibilityRepo
from profile.uow.account import AccountMixin
from profile.uow.organization import OrganizationMixin
from profile.uow.outbox import OutboxMixin
from profile.uow.person import PersonMixin

from core.uow.sqlalchemy import UnitOfWork


class VisibilityMixin:
    visibility: VisibilityRepo


class VisibilityHistoryMixin:
    visibility_history: VisibilityHistoryRepo


class VisibilityUOW(
    UnitOfWork,
    VisibilityMixin,
    VisibilityHistoryMixin,
    OutboxMixin,
    AccountMixin,
    OrganizationMixin,
    PersonMixin,
): ...
