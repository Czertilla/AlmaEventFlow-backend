from collections.abc import Collection
from profile.models.visibility import PersonFieldVisibilityHistoryORM as HistoryModel
from profile.models.visibility import PersonFieldVisibilityORM as Model
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from core.database.sqlalchemy.core import SQLAlchemyRepository


class VisibilityRepo(SQLAlchemyRepository[Model]):
    model = Model

    async def stored(
        self, field_key: str, among: Collection[UUID] | None
    ) -> dict[UUID, str]:
        stmt = select(Model.person_id, Model.audience).where(
            Model.field_key == field_key
        )
        if among is not None:
            stmt = stmt.where(Model.person_id.in_(list(among)))
        return {row.person_id: row.audience for row in (await self.execute(stmt)).all()}

    async def of_person(self, person_id: UUID) -> dict[str, str]:
        stmt = select(Model.field_key, Model.audience).where(
            Model.person_id == person_id
        )
        return {row.field_key: row.audience for row in (await self.execute(stmt)).all()}

    async def put(self, person_id: UUID, field_key: str, audience: str) -> None:
        await self.execute(
            insert(Model)
            .values(
                person_id=person_id,
                field_key=field_key,
                audience=audience,
                created_at=func.now(),
            )
            .on_conflict_do_update(
                index_elements=["person_id", "field_key"],
                set_={"audience": audience, "edited_at": func.now()},
            )
        )

    async def clear(self, person_id: UUID, field_key: str) -> None:
        await self.execute(
            delete(Model).where(
                Model.person_id == person_id, Model.field_key == field_key
            )
        )


class VisibilityHistoryRepo(SQLAlchemyRepository[HistoryModel]):
    model = HistoryModel

    async def record(
        self,
        person_id: UUID,
        field_key: str,
        *,
        old_audience: str | None,
        new_audience: str | None,
        actor_user_id: UUID,
        source: str,
    ) -> None:
        await self.add_one(
            {
                "person_id": person_id,
                "field_key": field_key,
                "old_audience": old_audience,
                "new_audience": new_audience,
                "actor_user_id": actor_user_id,
                "source": source,
            }
        )
