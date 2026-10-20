from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.config.settings import settings
from core.enum.config import DBManagerType

match settings.DB_DBMS:
    case DBManagerType.sqlite:
        from .engine.sqlite import engine, get_engine, get_url
    case DBManagerType.postgres:
        from .engine.pgsql import engine, get_engine, get_url

new_session = async_sessionmaker(engine, expire_on_commit=False)

class SessionFactory:
    @staticmethod
    def get_by_db_name(db_name: str) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(get_engine(get_url(db_name=db_name)))

