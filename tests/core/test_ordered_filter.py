from typing import Annotated, Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import SmallInteger, Uuid, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.filter.depends import FilterDepends
from core.filter.identity import id_search_clause
from core.filter.ordered import OrderedFilter
from user.models.user import UserORM


class SampleFilter(OrderedFilter):
    order_by: list[str] | None = ["created_at"]  # noqa: RUF012  # pydantic field default

    class Constants(OrderedFilter.Constants):
        model = UserORM
        order_fields = ("created_at", "username")


def test_allowed_fields_are_accepted_with_either_direction() -> None:
    assert SampleFilter.model_validate(
        {"order_by": "-created_at,username"}
    ).order_by == [
        "-created_at",
        "username",
    ]


def test_fields_outside_the_allowlist_are_rejected_even_when_the_model_has_them() -> (
    None
):
    with pytest.raises(ValidationError, match="not an allowed ordering field"):
        SampleFilter.model_validate({"order_by": "hashed_password"})


def test_the_default_ordering_is_valid() -> None:
    assert SampleFilter().order_by == ["created_at"]


def test_the_allowed_fields_are_documented_on_the_parameter() -> None:
    description = SampleFilter.model_fields["order_by"].description

    assert description is not None
    assert "created_at, username" in description


def test_the_allowed_fields_reach_the_openapi_schema() -> None:
    app = FastAPI()

    @app.get("/items")
    async def items(  # pyright: ignore[reportUnusedFunction]
        _: Annotated[SampleFilter, FilterDepends(SampleFilter)],
    ) -> None: ...

    parameters: list[dict[str, Any]] = app.openapi()["paths"]["/items"]["get"][
        "parameters"
    ]
    order_by = next(item for item in parameters if item["name"] == "order_by")

    assert "created_at, username" in order_by["description"]


class Base(DeclarativeBase):
    pass


class UuidRow(Base):
    __tablename__ = "uuid_row"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str]


class NumberRow(Base):
    __tablename__ = "number_row"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str]


class TextRow(Base):
    __tablename__ = "text_row"

    id: Mapped[str] = mapped_column(primary_key=True)


class UuidRowFilter(OrderedFilter):
    search: str | None = None

    class Constants(OrderedFilter.Constants):
        model = UuidRow
        search_model_fields = ["name"]  # noqa: RUF012


def _where(model: Any, term: str) -> str:
    clause = id_search_clause(model, term)
    if clause is None:
        return ""
    return str(clause.compile(dialect=postgresql.dialect()))


def test_a_full_uuid_is_matched_by_equality() -> None:
    assert _where(UuidRow, str(uuid4())) == "uuid_row.id = %(id_1)s::UUID"


def test_a_uuid_without_dashes_or_around_spaces_is_still_an_id() -> None:
    assert _where(UuidRow, f" {uuid4().hex} ") == "uuid_row.id = %(id_1)s::UUID"


@pytest.mark.parametrize("term", ["3f2a9c", "3F2A9C41-7B", str(uuid4())[:-1]])
def test_a_start_of_an_id_is_matched_by_prefix(term: str) -> None:
    assert "ILIKE" in _where(UuidRow, term)
    assert "CAST(uuid_row.id AS VARCHAR)" in _where(UuidRow, term)


@pytest.mark.parametrize("term", ["Иванов", "choir", "3f2a9", "3f2a9c x", "2026.05"])
def test_text_that_cannot_be_an_id_adds_no_clause(term: str) -> None:
    assert _where(UuidRow, term) == ""


def test_a_whole_number_is_matched_as_text_so_a_wide_value_cannot_overflow() -> None:
    assert _where(NumberRow, "007") == "CAST(number_row.id AS VARCHAR) = %(param_1)s"
    assert _where(NumberRow, "9" * 40) == ""
    assert _where(NumberRow, "a1") == ""


def test_a_model_without_a_numeric_or_uuid_id_adds_no_clause() -> None:
    assert _where(TextRow, str(uuid4())) == ""


def test_search_looks_in_the_columns_and_in_the_id() -> None:
    row_id = uuid4()
    query = UuidRowFilter(search=str(row_id)).filter(select(UuidRow))
    sql = str(query.compile(dialect=postgresql.dialect()))

    assert "uuid_row.name ILIKE" in sql
    assert "uuid_row.id = " in sql
    assert " OR " in sql


def test_an_empty_search_adds_no_clause_and_the_filter_keeps_its_value() -> None:
    blank = UuidRowFilter(search="")
    word = UuidRowFilter(search="choir")

    assert "WHERE" not in str(blank.filter(select(UuidRow)))
    assert "uuid_row.id" not in str(word.filter(select(UuidRow)).whereclause)
    assert (blank.search, word.search) == ("", "choir")
