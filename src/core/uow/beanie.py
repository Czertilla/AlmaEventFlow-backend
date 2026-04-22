from logging import getLogger
from pymongo import AsyncMongoClient
from pymongo.asynchronous.client_session import (
    AsyncClientSession,
    AsyncContextManager,
)
from core.uow.base import BaseUOW
from core.database.beanie.client import get_client


logger = getLogger(__name__)


class UnitOfWork(BaseUOW):
    """
    Implementation of the Unit of Work pattern using SQLAlchemy's AsyncSession.

    Manages database sessions and transactions.
    """

    def __init__(self, *, max_commit_time_ms: int | None = None):
        """
        Initializes the UnitOfWork with a new session factory.
        """
        super().__init__()
        self.client: AsyncMongoClient = get_client()
        self.max_commit_time_ms: int | None = max_commit_time_ms
        self.client_session: AsyncClientSession | None = None
        self.client_context: AsyncContextManager | None = None

    def _init_repo(self, repo_type):
        return repo_type(self.client_session)

    async def _on_aenter(self) -> None:
        """
        Enters the asynchronous context and creates a new database session.
        Automatically initializes all declared repositories.

        Returns:
            UnitOfWork: The UnitOfWork instance.
        """
        self.client_session = self.client.start_session()
        self.client_context = await self.client_session.start_transaction(
            max_commit_time_ms=self.max_commit_time_ms
        )
        await self.client_context.__aenter__()

    async def _on_aexit(self):
        if self.client_session:
            await self.client_context.__aexit__(None, None, None)
            await self.client_session.end_session()
        self.client_session = None
        self.client_context = None

    async def commit(self) -> None:
        """
        Commits the transaction.

        Args:
            flush: Whether to flush the session before committing.
        """
        if self.client_session and self.client_context:
            await self.client_session.commit_transaction()

    async def rollback(self) -> None:
        """
        Rolls back the transaction.
        """
        if self.client_session and self.client_context:
            await self.client_session.abort_transaction()
