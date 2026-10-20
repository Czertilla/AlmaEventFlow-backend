from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.database.sqlalchemy.session import new_session


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return new_session