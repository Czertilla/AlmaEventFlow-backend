from contextlib import AbstractAsyncContextManager
from logging import getLogger
from typing import Any, cast

from pymongo import AsyncMongoClient
from pymongo.asynchronous.client_session import AsyncClientSession

from core.database.beanie.client import get_client
from core.database.beanie.core import BeanieRepository
from core.uow.base import BaseUOW
from core.utils.abstract.repository import AbstractRepository

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
        self.client: AsyncMongoClient[dict[str, Any]] = get_client()
        self.max_commit_time_ms: int | None = max_commit_time_ms
        self.client_session: AsyncClientSession | None = None
        self.client_context: AbstractAsyncContextManager[Any] | None = None

    def _init_repo(self, repo_type: type[AbstractRepository]) -> AbstractRepository:
        assert self.client_session is not None
        return cast("type[BeanieRepository[Any, Any]]", repo_type)(
            self.client_session
        )

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
            assert self.client_context is not None
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
