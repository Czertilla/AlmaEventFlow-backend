from collections.abc import Iterable
from datetime import datetime
from profile.models.outbox import NotificationOutboxORM as Model
from typing import Any
from uuid import UUID

from sqlalchemy import select, update

from core.database.sqlalchemy.core import SQLAlchemyRepository


class NotificationOutboxRepo(SQLAlchemyRepository[Model]):
    model = Model

    async def enqueue(
        self,
        *,
        person_id: UUID | None = None,
        user_id: UUID | None = None,
        category: str,
        title: str,
        body: str,
        data: dict[str, Any],
        now: datetime,
    ) -> None:
        if person_id is None and user_id is None:
            raise ValueError("a notification needs a person or an account")
        await self.add_one(
            {
                "person_id": person_id,
                "user_id": user_id,
                "category": category,
                "title": title,
                "body": body,
                "data": data,
                "next_attempt_at": now,
            }
        )

    async def claim_due(self, limit: int, now: datetime) -> list[Model]:
        stmt = (
            select(Model)
            .where(Model.status == "pending", Model.next_attempt_at <= now)
            .order_by(Model.created_at, Model.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list((await self.execute(stmt)).scalars().all())

    async def mark_published(self, ids: Iterable[UUID], now: datetime) -> None:
        ids = list(ids)
        if ids:
            await self.execute(
                update(Model)
                .where(Model.id.in_(ids))
                .values(status="published", published_at=now)
            )

    async def mark_retry(
        self, row_id: UUID, attempts: int, next_attempt_at: datetime
    ) -> None:
        await self.execute(
            update(Model)
            .where(Model.id == row_id)
            .values(attempts=attempts, next_attempt_at=next_attempt_at)
        )

    async def mark_dead(self, row_id: UUID, attempts: int) -> None:
        await self.execute(
            update(Model)
            .where(Model.id == row_id)
            .values(status="dead", attempts=attempts)
        )
