from pydantic import BaseModel, Field
from typing import Generic, Self, TypeVar

from core.utils.pagination import get_offset, get_total_pages
from core.config.settings import settings

T = TypeVar("T")


class SPageParam(BaseModel):
    page: int = Field(default=0)
    limit: int = Field(gt=0, le=settings.MAX_PAGE_SIZE, default=10)

    @property
    def offset(self) -> int:
        return get_offset(self.page, self.limit)


class SPagination(SPageParam):
    total: int = Field()

    @classmethod
    def sql_validate(cls, page: int, limit: int, total: int) -> Self:
        instance = cls(page=page, limit=limit, total=total)
        instance.total = get_total_pages(total, limit)
        return instance


class SPage(BaseModel, Generic[T]):
    items: list[T]
    pagination: SPagination
