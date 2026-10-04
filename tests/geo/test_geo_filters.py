from typing import Any

import pytest
from support.filters import (
    assert_dto_parity,
    assert_ordering_documented,
    exercise_filter,
)

from geo.filter.address import AddressFilter
from geo.filter.city import CityFilter
from geo.filter.location import LocationFilter

FILTERS: list[Any] = [AddressFilter, CityFilter, LocationFilter]


@pytest.mark.parametrize("filter_cls", FILTERS, ids=lambda cls: cls.__name__)
def test_filter_and_dto_expose_the_same_fields(filter_cls: Any) -> None:
    assert_dto_parity(filter_cls)


@pytest.mark.parametrize("filter_cls", FILTERS, ids=lambda cls: cls.__name__)
def test_ordering_fields_are_documented(filter_cls: Any) -> None:
    assert_ordering_documented(filter_cls)


@pytest.mark.parametrize("filter_cls", FILTERS, ids=lambda cls: cls.__name__)
async def test_every_filter_and_ordering_runs_against_the_database(
    filter_cls: Any, sessionmaker_: Any
) -> None:
    await exercise_filter(sessionmaker_, filter_cls)
