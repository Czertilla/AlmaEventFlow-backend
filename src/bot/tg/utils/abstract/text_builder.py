from abc import ABC, abstractmethod
from enum import Enum


class ABCTextBuilder(ABC):
    lang: str

    @abstractmethod
    async def get_phrase(self, key: str | Enum, **kwargs) -> str:
        raise NotImplementedError()
