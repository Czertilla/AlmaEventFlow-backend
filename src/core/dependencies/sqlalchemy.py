from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies.session import async_sessionmaker, get_session_maker
from core.uow.sqlalchemy import UnitOfWork


class UOWDep:
    def __init__(
        self,
        uow_cls: type[UnitOfWork],
        *,
        sessionmaker: async_sessionmaker[AsyncSession] | None = None,
    ):
        self.uow_cls = uow_cls
        self.sessionmaker = sessionmaker

    def __call__(
        self,
        sessionmaker: async_sessionmaker[AsyncSession] = Depends(get_session_maker),
    ):
        return self.uow_cls(self.sessionmaker or sessionmaker)
