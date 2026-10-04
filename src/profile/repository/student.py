from profile.models.profile import ProfileORM
from profile.models.student import (
    StudentDegree,
    StudentGroupORM,
)
from profile.models.student import (
    StudentORM as Model,
)
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, Table, delete, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import selectinload

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    SearchRepositoryMixin,
    UpsertRepositoryMixin,
)


class StudentRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, UUID],
    UpsertRepositoryMixin[Model, UUID],
    SearchRepositoryMixin[Model],
):
    model = Model

    all_options = (
        selectinload(Model.person),
        selectinload(Model.group),
        selectinload(Model.profile).selectinload(ProfileORM.person),
        selectinload(Model.profile).joinedload(ProfileORM.diet),
        selectinload(Model.profile).selectinload(ProfileORM.workplace),
    )

    table: Table = cast(
        Table, Model.__table__
    )  # joined-table child: writes skip profile

    async def enroll(self, data: dict[str, Any]) -> None:
        await self.execute(insert(self.table).values(**data), flush=True)

    async def enroll_or_update(self, data: dict[str, Any]) -> None:
        stmt = pg_insert(self.table).values(**data)
        await self.execute(
            stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={k: v for k, v in data.items() if k != "id"},
            ),
            flush=True,
        )

    async def update_enrollment(self, id: UUID, data: dict[str, Any]) -> bool:
        if not data:
            return await self.exists_id(id)
        result = await self.execute(
            update(self.table).where(self.table.c.id == id).values(**data),
            flush=True,
        )
        return cast("CursorResult[Any]", result).rowcount > 0

    async def unenroll(self, id: UUID) -> None:
        await self.execute(delete(self.table).where(self.table.c.id == id))


class StudentGroupRepo(
    SQLAlchemyRepository[StudentGroupORM],
    IDRepositoryMixin[StudentGroupORM, int],
    UpsertRepositoryMixin[StudentGroupORM, int],
    SearchRepositoryMixin[StudentGroupORM],
):
    model = StudentGroupORM


class StudentDegreeRepo(
    SQLAlchemyRepository[StudentDegree],
    IDRepositoryMixin[StudentDegree, int],
    UpsertRepositoryMixin[StudentDegree, int],
    SearchRepositoryMixin[StudentDegree],
):
    model = StudentDegree
