from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from support.filters import (
    assert_dto_parity,
    assert_ordering_documented,
    exercise_filter,
)

from org.filter.collective import CollectiveFilter
from org.filter.faculty import FacultyFilter
from org.filter.organization import OrganizationFilter
from org.filter.university import UniversityFilter

FILTERS: list[Any] = [
    CollectiveFilter,
    FacultyFilter,
    OrganizationFilter,
    UniversityFilter,
]


@pytest.mark.parametrize("filter_cls", FILTERS, ids=lambda cls: cls.__name__)
def test_filter_and_dto_expose_the_same_fields(filter_cls: Any) -> None:
    assert_dto_parity(filter_cls)


@pytest.mark.parametrize("filter_cls", FILTERS, ids=lambda cls: cls.__name__)
def test_ordering_fields_are_documented(filter_cls: Any) -> None:
    assert_ordering_documented(filter_cls)


@pytest.mark.parametrize("filter_cls", FILTERS, ids=lambda cls: cls.__name__)
async def test_every_filter_and_ordering_runs_against_the_database(
    filter_cls: Any, org_sessionmaker: async_sessionmaker[AsyncSession]
) -> None:
    await exercise_filter(org_sessionmaker, filter_cls)
