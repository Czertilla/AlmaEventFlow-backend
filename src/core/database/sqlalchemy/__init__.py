from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config.settings import settings
from core.enum.config import DBManagerType

match settings.DB_DBMS:
    case DBManagerType.sqlite:
        from .engine.sqlite import engine
    case DBManagerType.postgres:
        from .engine.pgsql import engine

new_session = async_sessionmaker(engine, expire_on_commit=False)
