from fastapi import Depends

from core.dependencies.session import async_sessionmaker, get_session_maker
from core.utils.abstract.unit_of_work import ABCUnitOfWork


class UOWDep:
    def __init__(self, uow_cls: type[ABCUnitOfWork], *, sessionmaker=None):
        self.uow_cls = uow_cls
        self.sessionmaker = sessionmaker

    def __call__(
        self, sessionmaker: async_sessionmaker = Depends(get_session_maker)
    ):
        return self.uow_cls(self.sessionmaker or sessionmaker)
