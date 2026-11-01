from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.config.settings import settings
from core.database.sqlalchemy.engine.pgsql import get_engine, get_url
from core.database.sqlalchemy.session import new_session
from core.dependencies.uow import ModuleUOWDep

UOWDep = ModuleUOWDep("profile")


def profile_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if settings.MONOLITH:
        return async_sessionmaker(
            get_engine(get_url(db_name="profile")), expire_on_commit=False
        )
    return new_session
