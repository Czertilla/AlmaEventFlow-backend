from .sqlalchemy import UnitOfWork as SQLAlchemy
from .beanie import UnitOfWork as Beanie
from core.database.beanie.core import BeanieRepository
from core.database.sqlalchemy.core import SQLAlchemyRepository


class UnitOfWork(SQLAlchemy, Beanie):
    def __init__(
        self
    ):
        SQLAlchemy.__init__(self)
        Beanie.__init__(self)

    def _init_repo(self, repo_type):
        if issubclass(repo_type, BeanieRepository):
            return Beanie._init_repo(self, repo_type)
        if issubclass(repo_type, SQLAlchemyRepository):
            return SQLAlchemy._init_repo(self, repo_type)

    async def _on_aenter(self):
        await SQLAlchemy._on_aenter(self)
        await Beanie._on_aenter(self)

    async def _on_aexit(self):
        await SQLAlchemy._on_aexit(self)
        await Beanie._on_aexit(self)

    async def commit(self):
        await SQLAlchemy.commit(self)
        await Beanie.commit(self)

    async def rollback(self):
        await SQLAlchemy.rollback(self)
        await Beanie.rollback(self)
