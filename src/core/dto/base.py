from dataclasses import dataclass, field
from dataclasses import fields as dataclass_fields
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from _typeshed import DataclassInstance


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldsSetDTOMixin:
    fields_set: frozenset[str] = field(default_factory=frozenset)


def dto_dict(
    dto: Any, *, only_set: bool = False, exclude: set[str] | None = None
) -> dict[str, Any]:
    # shallow: asdict() would deep-copy values such as UploadFile
    fields_set = getattr(dto, "fields_set", None)
    exclude = exclude or set()
    result: dict[str, Any] = {}
    for f in dataclass_fields(dto):
        if f.name == "fields_set" or f.name in exclude:
            continue
        if only_set and fields_set is not None and f.name not in fields_set:
            continue
        result[f.name] = getattr(dto, f.name)
    return result


def dto_from_orm[T: DataclassInstance](orm: object, dto_cls: type[T]) -> T:
    return dto_cls(
        **{
            f.name: getattr(orm, f.name)
            for f in dataclass_fields(dto_cls)
            if f.name != "fields_set"
        }
    )
