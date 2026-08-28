from sqlalchemy.ext.asyncio import async_sessionmaker

from core.database.sqlalchemy.engine.pgsql import get_engine, get_url
from core.uow.sqlalchemy import UnitOfWork

_sessionmaker = async_sessionmaker(
    get_engine(get_url(db_name="bot")), expire_on_commit=False
)


class BotUnitOfWork(UnitOfWork):
    """Base for bot UOWs that always targets the ``bot`` database.

    Aiogram handlers construct these directly (``UserUOW()``) rather than
    through a FastAPI ``Depends`` chain, so they can't pick up the per-module
    sessionmaker that ``ModuleUOWDep`` wires for HTTP/Kafka routes when
    running inside the monolith. Binding the default sessionmaker here keeps
    them pointed at ``bot`` regardless of the process's global ``DB_NAME``.
    """

    def __init__(self, sessionmaker: async_sessionmaker | None = None):
        super().__init__(sessionmaker or _sessionmaker)
