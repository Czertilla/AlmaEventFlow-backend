from abc import ABC, abstractmethod
from typing import Any


class AbstractRepository(ABC):
    @abstractmethod
    def add_one() -> None:
        raise NotImplementedError

    @abstractmethod
    def get_one() -> Any | None:
        raise NotImplementedError


class AbstractSetRepository(ABC):
    @abstractmethod
    def get_many() -> list[Any]:
        raise NotImplementedError


class AbstractIdRepository(ABC):
    @abstractmethod
    def get_by_id() -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def exists() -> bool:
        raise NotImplementedError

    @abstractmethod
    def update_one() -> Any:
        raise NotImplementedError

    @abstractmethod
    def delete_one() -> bool:
        raise NotImplementedError


class AbstractORMRepository(ABC):
    @abstractmethod
    def merge() -> None:
        raise NotImplementedError

    @abstractmethod
    def flush() -> None:
        raise NotImplementedError

    @abstractmethod
    def commit() -> None:
        raise NotImplementedError


class AbstractReturningRepository(ABC):
    @abstractmethod
    def add_n_return() -> Any:
        raise NotImplementedError


class AbstractCountingRepository(ABC):
    @abstractmethod
    def count() -> int:
        raise NotImplementedError
