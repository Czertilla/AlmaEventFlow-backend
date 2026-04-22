from core.config.settings import settings
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

match settings.DB_DBMS:
    case "sqlite":
        from .engine.sqlite import engine, get_engine, get_url
    case "postgres":
        from .engine.pgsql import engine, get_engine, get_url

new_session = async_sessionmaker(engine, expire_on_commit=False)

class SessionFactory:
    @staticmethod
    def get_by_db_name(db_name: str) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(get_engine(get_url(db_name=db_name)))

