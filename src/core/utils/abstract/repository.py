from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import Result


class AbstractRepository(ABC):
    @abstractmethod
    async def execute(self, stmt, flush: bool = False) -> Result:
        raise NotImplementedError
    
    @abstractmethod
    async def add_one(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_one(self, *args: Any, **kwargs: Any) -> Any | None:
        raise NotImplementedError


class AbstractSetRepository(ABC):
    @abstractmethod
    async def get_many(self, *args: Any, **kwargs: Any) -> list[Any]:
        raise NotImplementedError


class AbstractIdRepository(ABC):
    @abstractmethod
    async def get_by_id(self, *args: Any, **kwargs: Any) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def exists_id(self, *args: Any, **kwargs: Any) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def update_one(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def delete_one(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


class AbstractORMRepository(ABC):
    @abstractmethod
    async def merge(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    async def flush(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError


class AbstractReturningRepository(ABC):
    @abstractmethod
    async def add_n_return(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class AbstractCountingRepository(ABC):
    @abstractmethod
    async def count(self, *args: Any, **kwargs: Any) -> int:
        raise NotImplementedError
