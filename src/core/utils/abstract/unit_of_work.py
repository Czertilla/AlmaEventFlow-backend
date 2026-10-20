from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from core.utils.abstract.repository import AbstractRepository


class ABCUnitOfWork(ABC):
    """Manages repositories and one transaction; usable as ``async with``."""

    def __init__(self):
        raise NotImplementedError

    @abstractmethod
    async def __aenter__(self) -> Self:
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, *args) -> None:
        raise NotImplementedError

    @abstractmethod
    def _init_repo(self, repo_type: type[AbstractRepository]):
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
    def is_transacting(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def _on_aexit(self):
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError
