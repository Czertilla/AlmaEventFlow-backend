from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql.base import ExecutableOption

from core.repository.person import PersonBaseRepo
from user.models.person import PersonORM


class PersonRepo(PersonBaseRepo[PersonORM]):
    model = PersonORM

    async def upsert(
        self, data: dict[str, Any], options: tuple[ExecutableOption, ...] = ()
    ) -> PersonORM | None:
        stmt = (
            insert(self.model)
            .values(**data)
            .on_conflict_do_nothing(
                index_elements=self.conflict_index_elements,
            )
            .options(*options)
            .returning(self.model)
        )
        return (await self.execute(stmt)).scalar_one_or_none()