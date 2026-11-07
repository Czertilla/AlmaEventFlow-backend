from collections.abc import Collection, Hashable
from profile.models.person import PersonORM
from profile.registry import Reference, Source
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnClause, column, delete, select, table, update

from core.database.sqlalchemy.core import SQLAlchemyRepository

StoredRow = tuple[UUID, Any, dict[str, Any]]


def _column(name: str) -> ColumnClause[Any]:
    return column(name)


class RegistryRowsRepo(SQLAlchemyRepository[PersonORM]):
    """Reads registry columns of any table by person, as the registry describes
    the table; a row comes back as `(person_id, row_id, values)`."""

    model = PersonORM

    async def rows(
        self,
        source: Source,
        parent: Source | None,
        columns: Collection[str],
        person_ids: Collection[UUID],
    ) -> list[StoredRow]:
        if not person_ids:
            return []
        names = sorted(set(columns))
        own_columns = {source.row, *names}
        if parent is None:
            assert source.person is not None
            own_columns.add(source.person)
        own = table(source.table, *(_column(name) for name in sorted(own_columns)))
        values = [own.c[name] for name in names]
        if parent is None:
            assert source.person is not None
            person = own.c[source.person]
            stmt = select(person, own.c[source.row], *values)
        else:
            assert parent.person is not None
            up = table(parent.table, _column(parent.row), _column(parent.person))
            person = up.c[parent.person]
            stmt = select(person, own.c[source.row], *values).join_from(
                own, up, up.c[parent.row] == own.c[source.row]
            )
        stmt = stmt.where(person.in_(list(person_ids))).order_by(own.c[source.row])
        return [
            (row[0], row[1], dict(zip(names, row[2:], strict=True)))
            for row in (await self.execute(stmt)).all()
        ]

    async def update_row(
        self, source: Source, row_id: Any, values: dict[str, Any]
    ) -> None:
        own = table(
            source.table, _column(source.row), *(_column(name) for name in values)
        )
        await self.execute(
            update(own).where(own.c[source.row] == row_id).values(values)
        )

    async def delete_rows(self, source: Source, row_ids: Collection[Any]) -> None:
        if not row_ids:
            return
        own = table(source.table, _column(source.row))
        await self.execute(delete(own).where(own.c[source.row].in_(list(row_ids))))

    async def labels(
        self, ref: Reference, keys: Collection[Hashable]
    ) -> dict[Any, Any]:
        if not keys:
            return {}
        ref_table = table(ref.table, _column(ref.key), _column(ref.label))
        stmt = select(ref_table.c[ref.key], ref_table.c[ref.label]).where(
            ref_table.c[ref.key].in_(list(keys))
        )
        return {row[0]: row[1] for row in (await self.execute(stmt)).all()}
