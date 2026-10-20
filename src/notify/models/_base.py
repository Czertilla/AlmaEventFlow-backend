import enum
from enum import StrEnum

from sqlalchemy import Enum
from sqlalchemy.orm import DeclarativeBase

from core.config.settings import settings
from core.database.sqlalchemy.core import BasePreference

if settings.MONOLITH:

    class ModuleBase(BasePreference, DeclarativeBase):  # pyright: ignore[reportRedeclaration]
        type_annotation_map = BasePreference.type_annotation_map
else:

    class ModuleBase: ...


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


def enum_column(enum_cls: type[StrEnum], name: str) -> Enum:
    """Builds a native postgres enum column persisting member values (not names)."""
    return Enum(enum_cls, name=name, values_callable=_enum_values)
