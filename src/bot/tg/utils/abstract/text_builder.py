from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ABCTextBuilder(ABC):
    lang: str

    @abstractmethod
    async def get_phrase(self, key: str | Enum, **kwargs: Any) -> str:
        raise NotImplementedError()
