from collections.abc import Iterable

from sqlalchemy import select, update

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.enum.notify import OutboxStatus

from notify.models.outbox import OutboxEventORM as Model


class OutboxRepo(SQLAlchemyRepository[Model]):
    model = Model

    async def claim_pending(self, limit: int) -> list[Model]:
        """Locks and returns the oldest pending rows, skipping rows already
        locked by a concurrent publisher."""
        stmt = (
            select(self.model)
            .where(self.model.status == OutboxStatus.pending)
            .order_by(self.model.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return (await self.execute(stmt)).scalars().all()

    async def mark_published(self, ids: Iterable[int]) -> None:
        ids = list(ids)
        if not ids:
            return
        await self.execute(
            update(self.model)
            .where(self.model.id.in_(ids))
            .values(status=OutboxStatus.published)
        )

    async def mark_failed(self, row_id: int) -> None:
        await self.execute(
            update(self.model)
            .where(self.model.id == row_id)
            .values(attempts=self.model.attempts + 1)
        )

    async def mark_dead(self, row_id: int) -> None:
        await self.execute(
            update(self.model)
            .where(self.model.id == row_id)
            .values(
                status=OutboxStatus.failed, attempts=self.model.attempts + 1
            )
        )
