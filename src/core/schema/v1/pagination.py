from typing import Self

from pydantic import BaseModel, Field

from core.config.settings import settings
from core.dto.pagination import PageParamDTO, PaginationDTO
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.utils.pagination import get_offset, get_total_pages


class PageParamV1(BaseModel, ToDTOMixinV1):
    __dto_cls__ = PageParamDTO

    page: int = Field(default=0)
    limit: int = Field(gt=0, le=settings.MAX_PAGE_SIZE, default=10)

    @property
    def offset(self) -> int:
        return get_offset(self.page, self.limit)


class PaginationV1(PageParamV1, FromDTOMixinV1):
    __dto_cls__ = PaginationDTO

    total: int = Field()

    @classmethod
    def sql_validate(cls, page: int, limit: int, total: int) -> Self:
        instance = cls(page=page, limit=limit, total=total)
        instance.total = get_total_pages(total, limit)
        return instance


class PageV1[T](BaseModel, FromDTOMixinV1):
    items: list[T]
    pagination: PaginationV1
