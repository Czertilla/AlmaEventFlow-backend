from sqlalchemy.orm import DeclarativeBase
from core.config.settings import settings
from core.database.sqlalchemy.core import BasePreference

if settings.MONOLITH:

    class ModuleBase(BasePreference, DeclarativeBase):
        # type_annotation_map is only honored from the declarative base's own
        # __dict__, so it must be set here explicitly (see core.Base).
        type_annotation_map = BasePreference.type_annotation_map
else:

    class ModuleBase: ...
