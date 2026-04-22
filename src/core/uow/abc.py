from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from core.repository.abc import AbstractRepository


class ABCUnitOfWork(ABC):
    """
    Abstract base class for Unit of Work implementations.

    Defines the interface for managing repositories and transactions.
    Supports variable number of repository types.
    """

    def __init__(self):
        """
        Initializes the Unit of Work.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> Self:
        """
        Enters the asynchronous context.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *args) -> None:
        """
        Exits the asynchronous context.

        Args:
            *args: Arguments passed from the context manager.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def _init_repo(self, repo_type: type[AbstractRepository]):
        """
        Initializes the repository of the given type.
        """
        raise NotImplementedError

    @abstractmethod
    async def _on_aenter(self):
        raise NotImplementedError

    @abstractmethod
    async def _on_aexit_error(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        raise NotImplementedError

    @abstractmethod
    async def _on_aexit(self):
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        """
        Commits the transaction.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        """
        Rolls back the transaction.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError
