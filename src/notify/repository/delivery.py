from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import IDRepositoryMixin
from core.enum.notify import DeliveryStatus

from notify.models.delivery import NotificationDeliveryORM as Model


class NotificationDeliveryRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
):
    model = Model

    async def get_due_retries(self, limit: int) -> list[Model]:
        """Locks deliveries whose backoff has elapsed, skipping rows already
        claimed by a concurrent retry worker."""
        stmt = (
            select(self.model)
            .where(
                self.model.status == DeliveryStatus.retry_scheduled,
                self.model.next_attempt_at.is_not(None),
                self.model.next_attempt_at <= datetime.now(timezone.utc),
            )
            .order_by(self.model.next_attempt_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return (await self.execute(stmt)).scalars().all()

    async def mark_pending(self, ids: Iterable[UUID]) -> None:
        ids = list(ids)
        if not ids:
            return
        await self.execute(
            update(self.model)
            .where(self.model.id.in_(ids))
            .values(status=DeliveryStatus.pending, next_attempt_at=None)
        )

    async def mark_failed(self, ids: Iterable[UUID], error: str) -> None:
        ids = list(ids)
        if not ids:
            return
        await self.execute(
            update(self.model)
            .where(self.model.id.in_(ids))
            .values(
                status=DeliveryStatus.failed,
                next_attempt_at=None,
                last_error=error,
            )
        )
