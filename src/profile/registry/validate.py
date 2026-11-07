from collections.abc import Iterable
from re import fullmatch

from sqlalchemy import LargeBinary, MetaData

from .field import Column, PersonalField, Source


class RegistryError(Exception):
    """The registry of personal data is misconfigured."""


def _source_problems(
    tables: set[str], sources: Iterable[Source], metadata: MetaData
) -> list[str]:
    found: list[str] = []
    by_table = {source.table: source for source in sources}
    for name in sorted(tables):
        source = by_table.get(name)
        if source is None:
            found.append(f"`{name}`: no source says how a row reaches its person")
            continue
        table = metadata.tables.get(name)
        if table is None:
            continue
        if (source.person is None) == (source.parent is None):
            found.append(f"`{name}`: a source names a person column or a parent")
        columns = [source.row, *([source.person] if source.person else [])]
        found.extend(
            f"`{name}`: no column `{name}.{column}`"
            for column in columns
            if column not in table.columns
        )
        if source.parent is not None:
            parent = by_table.get(source.parent)
            if parent is None or parent.person is None:
                found.append(f"`{name}`: the parent must reach the person itself")
    return found


def _reference_problems(
    field: PersonalField, column: Column, metadata: MetaData
) -> list[str]:
    if column.ref is None:
        return []
    if field.encrypted:
        return [f"{field.key}: an encrypted column cannot refer to a row"]
    table = metadata.tables.get(column.ref.table)
    if table is None:
        return [f"{field.key}: no table `{column.ref.table}`"]
    return [
        f"{field.key}: no column `{column.ref.table}.{name}`"
        for name in (column.ref.key, column.ref.label)
        if name not in table.columns
    ]


def problems(
    fields: Iterable[PersonalField],
    metadata: MetaData,
    sources: Iterable[Source] | None = None,
) -> list[str]:
    from .fields import all_sources

    found: list[str] = []
    seen: set[str] = set()
    tables: set[str] = set()
    fields = list(fields)
    for field in fields:
        tables.update(column.table for column in field.columns)
        if field.grantable and len({column.table for column in field.columns}) > 1:
            found.append(f"{field.key}: a grantable field lies in one table")
        if field.key in seen:
            found.append(f"{field.key}: the key is used twice")
        seen.add(field.key)
        if not fullmatch(r"[a-z_]+\.[a-z_]+", field.key):
            found.append(f"{field.key}: the key must look like `table.name`")
        if field.audience_default.rank < field.audience_min.rank:
            found.append(f"{field.key}: the default is narrower than the minimum")
        if field.audience_default.rank > field.audience_max.rank:
            found.append(f"{field.key}: the default is wider than the maximum")
        head = field.audience_default_for_unit_head
        if head is not None and not (
            field.audience_min.rank <= head.rank <= field.audience_max.rank
        ):
            found.append(f"{field.key}: the unit head default is out of range")
        if field.encrypted and field.audience_max.rank > 0:
            found.append(f"{field.key}: an encrypted field cannot be opened")
        if not field.columns:
            found.append(f"{field.key}: no columns")
        for column in field.columns:
            found.extend(_reference_problems(field, column, metadata))
            table = metadata.tables.get(column.table)
            names = {column.column, *([column.where[0]] if column.where else [])}
            if table is None:
                found.append(f"{field.key}: no table `{column.table}`")
                continue
            found.extend(
                f"{field.key}: no column `{column.table}.{name}`"
                for name in sorted(names)
                if name not in table.columns
            )
            stored = table.columns.get(column.column)
            if stored is None:
                continue
            binary = isinstance(stored.type, LargeBinary)
            if field.encrypted and not binary:
                found.append(
                    f"{field.key}: `{column.table}.{column.column}` must be bytea"
                )
            if not field.encrypted and binary:
                found.append(
                    f"{field.key}: `{column.table}.{column.column}` holds ciphertext"
                )
    found.extend(
        _source_problems(
            tables, all_sources() if sources is None else sources, metadata
        )
    )
    return found


def validate_registry() -> None:
    from profile.models import PersonORM

    from .fields import all_fields

    found = problems(all_fields(), PersonORM.metadata)
    if found:
        raise RegistryError("; ".join(found))
