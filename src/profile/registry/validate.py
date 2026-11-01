from collections.abc import Iterable
from re import fullmatch

from sqlalchemy import LargeBinary, MetaData

from .field import PersonalField


class RegistryError(Exception):
    """The registry of personal data is misconfigured."""


def problems(fields: Iterable[PersonalField], metadata: MetaData) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for field in fields:
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
    return found


def validate_registry() -> None:
    from profile.models import PersonORM

    from .fields import all_fields

    found = problems(all_fields(), PersonORM.metadata)
    if found:
        raise RegistryError("; ".join(found))
