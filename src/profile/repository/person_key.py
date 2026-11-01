from collections.abc import Collection
from profile.models.person_key import PersonKeyORM as Model
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from core.database.sqlalchemy.core import SQLAlchemyRepository


class PersonKeyRepo(SQLAlchemyRepository[Model]):
    model = Model

    async def of_persons(self, person_ids: Collection[UUID]) -> dict[UUID, Model]:
        if not person_ids:
            return {}
        stmt = (
            select(Model)
            .where(Model.person_id.in_(list(person_ids)))
            .execution_options(populate_existing=True)
        )
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
