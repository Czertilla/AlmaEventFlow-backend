from sqlalchemy.ext.asyncio import async_sessionmaker
from core.config.settings import settings

match settings.DB_DBMS:
    case "sqlite":
        from .engine.sqlite import engine
    case "postgres":
        from .engine.pgsql import engine

new_session = async_sessionmaker(engine, expire_on_commit=False)
