from dataclasses import dataclass
from typing import Protocol

from core.utils.pagination import get_offset


class PageParams(Protocol):
    @property
    def page(self) -> int: ...

    @property
    def limit(self) -> int: ...

    @property
    def offset(self) -> int: ...


@dataclass(frozen=True, slots=True)
class PageParamDTO:
    page: int = 0
    limit: int = 10

    @property
    def offset(self) -> int:
        return get_offset(self.page, self.limit)


@dataclass(frozen=True, slots=True)
class PaginationDTO:
    page: int
    limit: int
    total: int


@dataclass(frozen=True, slots=True)
class PageDTO[T]:
    items: list[T]
    pagination: PaginationDTO
