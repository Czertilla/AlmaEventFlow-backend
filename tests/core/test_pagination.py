from dataclasses import dataclass

from pydantic import BaseModel

from core.dto.pagination import PageDTO, PageParamDTO, PaginationDTO
from core.schema.v1.mixin.dto import FromDTOMixinV1
from core.schema.v1.pagination import PageParamV1, PageV1


@dataclass(frozen=True)
class ItemDTO:
    id: int
    name: str


class ItemRead(BaseModel, FromDTOMixinV1):
    id: int
    name: str


def test_page_from_dto_converts_items_and_keeps_pagination():
    page_dto = PageDTO(
        items=[ItemDTO(id=1, name="a"), ItemDTO(id=2, name="b")],
        pagination=PaginationDTO(page=1, limit=2, total=5),
    )

    page = PageV1[ItemRead].from_dto(page_dto)

    assert page.items == [ItemRead(id=1, name="a"), ItemRead(id=2, name="b")]
    pagination = page.pagination
    assert (pagination.page, pagination.limit, pagination.total) == (1, 2, 5)


def test_page_can_report_the_page_count_as_its_total():
    page_dto = PageDTO(
        items=[ItemDTO(id=1, name="a")],
        pagination=PaginationDTO(page=0, limit=2, total=5),
    )

    page = PageV1[ItemRead].from_dto_with_page_count(page_dto)

    assert page.pagination.total == 3


def test_page_param_to_dto_roundtrip():
    dto = PageParamV1(page=3, limit=5).to_dto()

    assert dto == PageParamDTO(page=3, limit=5)
    assert dto.offset == 15
