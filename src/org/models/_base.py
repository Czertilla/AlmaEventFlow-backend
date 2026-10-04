from sqlalchemy.orm import DeclarativeBase

from core.config.settings import settings
from core.database.sqlalchemy.core import BasePreference

if settings.MONOLITH:

    class ModuleBase(BasePreference, DeclarativeBase):
        type_annotation_map = BasePreference.type_annotation_map
else:

    class ModuleBase: ...
