from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from core.config.settings import settings
from core.database.sqlalchemy.engine.pgsql import get_engine, get_url
from core.dependencies.sqlalchemy import UOWDep as Base


def ModuleUOWDep(module_name: str) -> type[Base]:  # noqa: N802  # a DI factory named like a class
    class Cls(Base):
        if settings.MONOLITH:
            sessionmaker = async_sessionmaker(
                get_engine(get_url(db_name=module_name)), expire_on_commit=False
            )

            def __init__(self, uow_cls: Any, *, sessionmaker: Any = sessionmaker):
                super().__init__(uow_cls, sessionmaker=sessionmaker)

    return Cls
