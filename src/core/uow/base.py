from types import TracebackType
from typing import get_type_hints
from logging import getLogger
from core.utils.abstract.unit_of_work import ABCUnitOfWork
from core.utils.abstract.repository import AbstractRepository

logger = getLogger(__name__)


class BaseUOW(ABCUnitOfWork):
    def __init__(self):
        self._repositories: dict[str, AbstractRepository] = {}
        self.transacting = False

    def register_repository(self, name: str, repo: AbstractRepository) -> None:
        """
        Registers a repository in the UnitOfWork.
        """
        setattr(self, name, repo)
        self._repositories[name] = repo

    def __init_subclass__(cls, **kwargs):
        """
        Scans the subclass for repository type annotations and prepares them for registration.
        """
        super().__init_subclass__(**kwargs)
        cls._repository_types = {
            name: typ
            for name, typ in get_type_hints(cls).items()
            if isinstance(typ, type) and issubclass(typ, AbstractRepository)
        }

    async def _on_aexit_error(self, exc_type, exc_val, exc_tb):
        return await self.rollback()

    async def __aenter__(self):
        self.transacting = True
        await self._on_aenter()
        for name, repo_type in self._repository_types.items():
            repo_instance = self._init_repo(repo_type)
            self.register_repository(name, repo_instance)

        logger.debug(
            f"Repositories initialized: {list(self._repositories.keys())}"
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Exits the asynchronous context, rolling back the transaction and closing the session.
        Automatically cleans up all repositories.
        """
        self.transacting = False
        logger.debug("Clean up repositories")
        for name in list(self._repositories.keys()):
            delattr(self, name)
        self._repositories.clear()

        if exc_type is not None:
            logger.exception(
                f"Exception during {self.__class__.__name__} transaction execution",
                exc_info=(exc_type, exc_val, exc_tb),
            )
            await self._on_aexit_error(exc_type, exc_val, exc_tb)
        await self._on_aexit()

    def is_transacting(self):
        return self.transacting
