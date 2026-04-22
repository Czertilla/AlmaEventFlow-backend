from sqlalchemy.ext.asyncio import async_sessionmaker

from core.database.sqlalchemy.session import new_session


def get_session_maker() -> async_sessionmaker:
    return new_session