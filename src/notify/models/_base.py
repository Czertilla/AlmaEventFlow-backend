from enum import StrEnum

from sqlalchemy import Enum
from sqlalchemy.orm import DeclarativeBase
from core.config.settings import settings
from core.database.sqlalchemy.core import BasePreference

if settings.MONOLITH:

    class ModuleBase(BasePreference, DeclarativeBase):
        type_annotation_map = BasePreference.type_annotation_map
else:

    class ModuleBase: ...


def enum_column(enum_cls: type[StrEnum], name: str) -> Enum:
    """Builds a native postgres enum column persisting member values (not names)."""
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda enum: [member.value for member in enum],
    )
