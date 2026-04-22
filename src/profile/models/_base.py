from sqlalchemy.orm import DeclarativeBase
from core.config.settings import settings

if settings.MONOLITH:

    class ModuleBase(DeclarativeBase): ...
else:

    class ModuleBase: ...
