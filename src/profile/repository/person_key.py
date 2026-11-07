from collections.abc import Collection
from datetime import datetime
from profile.models.person_key import PersonKeyORM as Model
from typing import Literal
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from core.database.sqlalchemy.core import SQLAlchemyRepository

Lock = Literal["share", "update"]


class PersonKeyRepo(SQLAlchemyRepository[Model]):
    model = Model

    async def of_persons(
        self, person_ids: Collection[UUID], *, lock: Lock | None = None
    ) -> dict[UUID, Model]:
        """The keys of the persons; `share` holds them against a rotation or a
        destruction until the end of the transaction, `update` against any
        other writer too."""
        if not person_ids:
            return {}
        stmt = (
            select(Model)
            .where(Model.person_id.in_(list(person_ids)))
            .execution_options(populate_existing=True)
        )
        if lock is not None:
            stmt = stmt.with_for_update(read=lock == "share")
        rows = (await self.execute(stmt)).scalars().all()
        return {row.person_id: row for row in rows}

    async def insert_if_absent(
        self, person_id: UUID, wrapped_dek: bytes, key_ref: str, dek_version: int
    ) -> bool:
        stmt = (
            insert(Model)
            .values(
                person_id=person_id,
                wrapped_dek=wrapped_dek,
                key_ref=key_ref,
                dek_version=dek_version,
                created_at=func.now(),
            )
            .on_conflict_do_nothing(index_elements=["person_id"])
            .returning(Model.person_id)
        )
        return (await self.execute(stmt)).scalar_one_or_none() is not None

    async def replace(
        self,
        person_id: UUID,
        wrapped_dek: bytes,
        key_ref: str,
        dek_version: int,
        rotated_at: datetime | None,
    ) -> None:
        await self.execute(
            update(Model)
            .where(Model.person_id == person_id)
            .values(
                wrapped_dek=wrapped_dek,
                key_ref=key_ref,
                dek_version=dek_version,
                rotated_at=rotated_at,
            )
        )

    async def rewrap(self, person_id: UUID, wrapped_dek: bytes, key_ref: str) -> None:
        await self.execute(
            update(Model)
            .where(Model.person_id == person_id)
            .values(wrapped_dek=wrapped_dek, key_ref=key_ref)
        )

    async def destroy(self, person_id: UUID, at: datetime) -> None:
        await self.execute(
            update(Model)
            .where(Model.person_id == person_id)
            .values(wrapped_dek=None, key_ref=None, destroyed_at=at)
        )

    async def count_not_on(self, key_ref: str) -> int:
        stmt = select(func.count()).where(
            Model.wrapped_dek.is_not(None), Model.key_ref.is_distinct_from(key_ref)
        )
        return (await self.execute(stmt)).scalar_one()

    async def lock_not_on(self, key_ref: str, limit: int) -> list[Model]:
        """A batch of live keys wrapped otherwise than `key_ref`, locked for the
        transaction."""
        stmt = (
            select(Model)
            .where(
                Model.wrapped_dek.is_not(None), Model.key_ref.is_distinct_from(key_ref)
            )
            .order_by(Model.person_id)
            .limit(limit)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return list((await self.execute(stmt)).scalars().all())

    async def rotation_candidates(
        self, person_ids: Collection[UUID] | None, before: datetime | None
    ) -> list[UUID]:
        stmt = select(Model.person_id).where(Model.wrapped_dek.is_not(None))
        if person_ids is not None:
            stmt = stmt.where(Model.person_id.in_(list(person_ids)))
        if before is not None:
            stmt = stmt.where(
                or_(
                    Model.rotated_at < before,
                    Model.rotated_at.is_(None) & (Model.created_at < before),
                )
            )
        return list((await self.execute(stmt.order_by(Model.person_id))).scalars())

    async def by_key_ref(self) -> dict[str, int]:
        stmt = (
            select(Model.key_ref, func.count())
            .where(Model.wrapped_dek.is_not(None))
            .group_by(Model.key_ref)
        )
        return {
            str(key_ref): count for key_ref, count in (await self.execute(stmt)).all()
        }

    async def by_dek_version(self) -> dict[int, int]:
        stmt = (
            select(Model.dek_version, func.count())
            .where(Model.wrapped_dek.is_not(None))
            .group_by(Model.dek_version)
        )
        return dict((await self.execute(stmt)).tuples().all())

    async def destroyed(self) -> int:
        stmt = select(func.count()).where(Model.wrapped_dek.is_(None))
        return (await self.execute(stmt)).scalar_one()
