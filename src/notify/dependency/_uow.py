from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config.settings import settings
from core.database.sqlalchemy.engine.pgsql import get_engine, get_url
from core.database.sqlalchemy.session import new_session
from core.dependencies.uow import ModuleUOWDep

UOWDep = ModuleUOWDep("notify")


def notify_sessionmaker() -> async_sessionmaker:
    """Notify-scoped session factory for background workers that run outside the
    request lifecycle (and thus outside FastAPI dependency injection)."""
    if settings.MONOLITH:
        return async_sessionmaker(
            get_engine(get_url(db_name="notify")), expire_on_commit=False
        )
    return new_session
