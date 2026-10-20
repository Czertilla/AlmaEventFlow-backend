from collections.abc import Awaitable, Callable

from sqlalchemy import event
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import ConnectionPoolEntry
from sqlalchemy.util.concurrency import await_only

from core.config.settings import settings


def sync_as_async[**P, R](fn: Callable[P, Awaitable[R]]) -> Callable[P, R]:
    def go(*arg: P.args, **kw: P.kwargs) -> R:
        return await_only(fn(*arg, **kw))

    return go

def get_url(db_name: str = settings.DB_NAME):
    return f"sqlite+aiosqlite:///{db_name}.db"

def get_engine(url: str = get_url()) -> AsyncEngine:
    engine = create_async_engine(url)

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(
        dbapi_connection: DBAPIConnection, connection_record: ConnectionPoolEntry
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")

        cursor.close()

    return engine


engine = get_engine()

