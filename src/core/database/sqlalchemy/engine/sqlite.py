from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.util.concurrency import await_only
from sqlalchemy import event

from core.config.settings import settings


def sync_as_async(fn):
    def go(*arg, **kw):
        return await_only(fn(*arg, **kw))

    return go

def get_url(db_name: str = settings.DB_NAME):
    return f"sqlite+aiosqlite:///{db_name}.db"

def get_engine(url: str = get_url()) -> AsyncEngine:
    engine = create_async_engine(url)

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")

        cursor.close()

    return engine


engine = get_engine()

