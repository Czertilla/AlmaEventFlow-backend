from core.database.sqlalchemy import new_session
from sqlalchemy.ext.asyncio import async_sessionmaker
from core.uow.base import BaseUOW
from logging import getLogger
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Self

logger = getLogger(__name__)


class UnitOfWork(BaseUOW):
    """
    Implementation of the Unit of Work pattern using SQLAlchemy's AsyncSession.

    Manages database sessions and transactions.
    """

    def __init__(self, sessionmaker: async_sessionmaker | None = None):
        """
        Initializes the UnitOfWork with a new session factory.
        """
        super().__init__()
        self.session_factory: async_sessionmaker = sessionmaker or new_session
        self.session: AsyncSession | None = None

    def __call__(self) -> Self:
        """
        Returns a new UnitOfWork instance with the same session factory.
        """
        return self.__class__(self.session_factory)

    def _init_repo(self, repo_type):
        return repo_type(self.session)

    async def _on_aenter(self) -> Self:
        """
        Enters the asynchronous context and creates a new database session.
        Automatically initializes all declared repositories.

        Returns:
            UnitOfWork: The UnitOfWork instance.
        """
        self.session = self.session_factory()

    async def _on_aexit(self):
        if self.session:
            await self.session.close()
        self.session = None

    async def commit(self, flush: bool = False) -> None:
        """
        Commits the transaction.

        Args:
            flush: Whether to flush the session before committing.
        """
        if self.session:
            if flush:
                await self.session.flush()
            await self.session.commit()

    async def rollback(self) -> None:
        """
        Rolls back the transaction.
        """
        if self.session:
            await self.session.rollback()
