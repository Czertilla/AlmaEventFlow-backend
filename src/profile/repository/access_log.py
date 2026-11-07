from collections.abc import Collection, Sequence
from datetime import datetime
from profile.models.access_log import SensitiveAccessLogORM as Model
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.dto.pagination import PageParams


class AccessLogRepo(SQLAlchemyRepository[Model]):
    model = Model

    async def record_many(self, rows: Sequence[dict[str, Any]]) -> None:
        if rows:
            await self.session.execute(insert(Model), list(rows))

    async def notified_since(
        self, actor_user_id: UUID, subjects: Collection[UUID], since: datetime
    ) -> set[UUID]:
        if not subjects:
            return set()
        stmt = (
            select(Model.subject_person_id)
            .where(
                Model.actor_user_id == actor_user_id,
                Model.subject_person_id.in_(list(subjects)),
                Model.notified.is_(True),
                Model.created_at >= since,
            )
            .distinct()
        )
        return set((await self.execute(stmt)).scalars().all())

    async def of_subject(
        self, subject_id: UUID, page: PageParams
    ) -> tuple[list[Model], int]:
        where = Model.subject_person_id == subject_id
        total = (
            await self.execute(select(func.count()).select_from(Model).where(where))
        ).scalar_one()
        rows = (
            await self.execute(
                select(Model)
                .where(where)
                .order_by(Model.created_at.desc(), Model.id.desc())
                .offset(page.offset)
                .limit(page.limit)
            )
        ).scalars()
        return list(rows), total
