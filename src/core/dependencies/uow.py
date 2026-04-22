from core.config.settings import settings
from core.database.sqlalchemy.engine.pgsql import get_url, get_engine
from core.dependencies.sqlalchemy import UOWDep as Base


def ModuleUOWDep(module_name):
    class Cls(Base):
        if settings.MONOLITH:
            from sqlalchemy.ext.asyncio import async_sessionmaker

            sessionmaker = async_sessionmaker(
                get_engine(get_url(db_name=module_name)), expire_on_commit=False
            )

            def __init__(self, uow_cls, *, sessionmaker=sessionmaker):
                super().__init__(uow_cls, sessionmaker=sessionmaker)

    return Cls
