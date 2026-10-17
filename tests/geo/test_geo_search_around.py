from typing import Any

import pytest
from support.geocoder import (
    SUZDAL_PLACE,
    Maker,
    Published,
    RichStubGeocoder,
    StubGeocoder,
    address_of,
    count_rows,
    moscow_house,
    store_address,
    suzdal,
)

from geo.dto.point import PointDTO
from geo.dto.search import PlaceDTO, SearchQueryDTO
from geo.geocoder.base import GeocoderError
from geo.models.address import AddressORM
from geo.models.city import CityORM
from geo.service.external import ExternalSearch
from geo.service.search import SearchService
from geo.uow.address import AddressUOW

MOSCOW = ("Россия", "Москва", "Москва")
CENTRE = (55.7500, 37.6000)
NEAR = PointDTO(lat=CENTRE[0], lon=CENTRE[1])
SUZDAL_CENTRE = PointDTO(lat=SUZDAL_PLACE.lat, lon=SUZDAL_PLACE.lon)


@pytest.fixture(autouse=True)
def fetches(monkeypatch: pytest.MonkeyPatch) -> list[PointDTO]:
    asked: list[PointDTO] = []

    def schedule(point: PointDTO, **_: Any) -> None:
        asked.append(point)

    monkeypatch.setattr("geo.service.search.schedule_live_fetch", schedule)
    return asked


def _search(
    sessionmaker_: Maker, geocoder: StubGeocoder | None = None
) -> SearchService:
    external = ExternalSearch(geocoder) if geocoder else None
    return SearchService(AddressUOW(sessionmaker_), external)


async def _near(sessionmaker_: Maker, house: str, dlat: float, dlon: float = 0.0):
    return await store_address(
        sessionmaker_,
        MOSCOW,
        "Тверская улица",
        house,
        (CENTRE[0] + dlat, CENTRE[1] + dlon),
    )


def _names(result: Any) -> list[str]:
    return [address_of(hit).name for hit in result.items]


def _created(published: Published) -> list[Any]:
    return [payload for name, payload in published if name == "on_address_created"]


async def test_a_point_with_few_stored_addresses_lists_the_houses_around_it(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _near(sessionmaker_, "1", 0.0)
    await _near(sessionmaker_, "3", 0.0010)
    geocoder = RichStubGeocoder(
        found=[],
        nearby=[
            moscow_house(
                "Арбат", "1", lat=CENTRE[0] + 0.0004, lon=CENTRE[1], source_id="node/21"
            ),
            moscow_house(
                "Арбат", "3", lat=CENTRE[0] + 0.0030, lon=CENTRE[1], source_id="node/22"
            ),
        ],
    )

    result = await _search(sessionmaker_, geocoder).search(SearchQueryDTO(near=NEAR))

    assert _names(result) == [
        "Тверская улица, 1",
        "Арбат, 1",
        "Тверская улица, 3",
        "Арбат, 3",
    ]
    assert [hit.origin for hit in result.items] == [
        "local",
        "external",
        "local",
        "external",
    ]
    assert geocoder.nearby_calls == [(NEAR, 2.0, 10)]
    assert (result.external.state, result.external.provider) == ("ok", "stub")
    assert (geocoder.calls, geocoder.place_calls) == ([], [])
    assert await count_rows(sessionmaker_, AddressORM) == 4
    assert [[item.name for item in batch] for batch in _created(published)] == [
        ["Арбат, 1", "Арбат, 3"]
    ]


async def test_enough_stored_addresses_close_to_the_point_need_no_provider(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    for number, shift in (("1", 0.0), ("2", 0.0004), ("3", 0.0008)):
        await _near(sessionmaker_, number, shift)
    geocoder = RichStubGeocoder(found=[], nearby=[moscow_house("Арбат", "1")])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(near=NEAR, limit=3)
    )

    assert _names(result) == [
        "Тверская улица, 1",
        "Тверская улица, 2",
        "Тверская улица, 3",
    ]
    assert geocoder.nearby_calls == []
    assert result.external.state == "skipped"


async def test_stored_addresses_that_are_too_far_do_not_count_as_close(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    for number, shift in (("1", 0.03), ("2", 0.031), ("3", 0.032)):
        await _near(sessionmaker_, number, shift)
    geocoder = RichStubGeocoder(
        found=[], nearby=[moscow_house("Арбат", "1", lat=CENTRE[0])]
    )

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(near=NEAR, limit=3)
    )

    assert _names(result)[0] == "Арбат, 1"
    assert len(geocoder.nearby_calls) == 1


async def test_a_request_that_opts_out_never_asks_the_provider(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = RichStubGeocoder(found=[], nearby=[moscow_house("Арбат", "1")])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(near=NEAR, external=False)
    )

    assert geocoder.nearby_calls == []
    assert (result.items, result.external.state) == ([], "skipped")


async def test_a_request_that_opts_out_does_not_start_the_background_fetch(
    sessionmaker_: Maker, city_id: int, published: Published, fetches: list[PointDTO]
) -> None:
    await _search(sessionmaker_, RichStubGeocoder(found=[])).search(
        SearchQueryDTO(near=NEAR, external=False)
    )

    assert fetches == []


async def test_a_point_the_user_marked_starts_the_background_fetch(
    sessionmaker_: Maker, city_id: int, published: Published, fetches: list[PointDTO]
) -> None:
    await _search(sessionmaker_, RichStubGeocoder(found=[])).search(
        SearchQueryDTO(near=NEAR)
    )

    assert fetches == [NEAR]


async def test_a_typed_text_only_biased_to_the_map_does_not_start_the_background_fetch(
    sessionmaker_: Maker, city_id: int, published: Published, fetches: list[PointDTO]
) -> None:
    await _near(sessionmaker_, "1", 0.0)

    await _search(sessionmaker_, RichStubGeocoder(found=[])).search(
        SearchQueryDTO(query="тверская 1", near=NEAR)
    )

    assert fetches == []


async def test_only_locations_asked_for_means_no_houses(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = RichStubGeocoder(found=[], nearby=[moscow_house("Арбат", "1")])

    await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(near=NEAR, kinds=("location",))
    )

    assert geocoder.nearby_calls == []


async def test_a_failing_provider_leaves_the_stored_answer_and_says_why(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _near(sessionmaker_, "1", 0.0)
    geocoder = RichStubGeocoder(found=[], nearby_error=GeocoderError("HTTP 503"))

    result = await _search(sessionmaker_, geocoder).search(SearchQueryDTO(near=NEAR))

    assert _names(result) == ["Тверская улица, 1"]
    assert result.external.state == "error"


async def test_without_a_provider_the_nearest_stored_addresses_are_the_answer(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _near(sessionmaker_, "5", 0.0040)
    await _near(sessionmaker_, "1", 0.0)

    result = await _search(sessionmaker_).search(SearchQueryDTO(near=NEAR))

    assert _names(result) == ["Тверская улица, 1", "Тверская улица, 5"]
    assert result.external.state == "skipped"


async def test_a_house_the_provider_lists_that_is_already_stored_is_not_added_twice(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _near(sessionmaker_, "1", 0.0)
    geocoder = RichStubGeocoder(
        found=[],
        nearby=[
            moscow_house(
                "Тверская улица",
                "1",
                lat=CENTRE[0] + 0.0002,
                lon=CENTRE[1],
                city="Москва",
            ),
            moscow_house("Арбат", "1", lat=CENTRE[0] + 0.0010, lon=CENTRE[1]),
        ],
    )

    result = await _search(sessionmaker_, geocoder).search(SearchQueryDTO(near=NEAR))

    assert _names(result) == ["Тверская улица, 1", "Арбат, 1"]
    assert await count_rows(sessionmaker_, AddressORM) == 2


async def test_a_named_settlement_lists_the_addresses_nearest_to_its_centre(
    sessionmaker_: Maker,
    city_id: int,
    published: Published,
    fetches: list[PointDTO],
) -> None:
    geocoder = RichStubGeocoder(
        found=[],
        place=SUZDAL_PLACE,
        nearby=[
            suzdal("Ленина улица", "9", lat=56.4300, lon=40.4500, source_id="node/32"),
            suzdal(
                "Кремлёвская улица", "6", lat=56.4195, lon=40.4490, source_id="node/31"
            ),
            suzdal(
                "Советская улица", "1", lat=56.4240, lon=40.4490, source_id="node/33"
            ),
        ],
    )

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="Суздаль")
    )

    assert _names(result) == [
        "Кремлёвская улица, 6",
        "Советская улица, 1",
        "Ленина улица, 9",
    ]
    assert result.place == PlaceDTO(
        name="Суздаль",
        region="Владимирская область",
        country="Россия",
        lat=SUZDAL_PLACE.lat,
        lon=SUZDAL_PLACE.lon,
        bbox=SUZDAL_PLACE.bbox,
    )
    assert geocoder.place_calls == ["Суздаль"]
    assert geocoder.nearby_calls == [(SUZDAL_CENTRE, 2.0, 10)]
    assert {a.locality for a in map(address_of, result.items)} == {
        "Суздаль, Владимирская область, Россия"
    }
    assert fetches == [SUZDAL_CENTRE]
    assert await count_rows(sessionmaker_, CityORM) == 2


async def test_stored_addresses_of_the_settlement_are_listed_and_far_ones_are_not(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await store_address(
        sessionmaker_, MOSCOW, "Суздальская улица", "10", (55.7375, 37.8469)
    )
    local = await store_address(
        sessionmaker_,
        ("Россия", "Владимирская область", "Суздаль"),
        "Ленина улица",
        "88",
        (56.4224, 40.4485),
    )
    geocoder = RichStubGeocoder(found=[], place=SUZDAL_PLACE, nearby=[suzdal()])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="суздаль", limit=5)
    )

    assert [address_of(hit).id for hit in result.items][1] == local.id
    assert _names(result) == ["Кремлёвская улица, 6", "Ленина улица, 88"]
    assert result.place is not None


async def test_a_street_the_answer_already_has_is_not_taken_for_a_settlement(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await store_address(sessionmaker_, MOSCOW, "Тверская улица", "7", CENTRE)
    geocoder = RichStubGeocoder(found=[], place=SUZDAL_PLACE, nearby=[suzdal()])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="тверская")
    )

    assert result.place is None
    assert geocoder.place_calls == []
    assert _names(result) == ["Тверская улица, 7"]


async def test_a_provider_that_finds_no_settlement_leaves_the_text_search_to_run(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = RichStubGeocoder(
        found=[moscow_house("Тверская улица", "7")], place=None, nearby=[suzdal()]
    )

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="тверская", near=NEAR)
    )

    assert result.place is None
    assert geocoder.place_calls == ["тверская"]
    assert geocoder.place_nears == [NEAR]
    assert [query for query, _, _ in geocoder.calls] == ["тверская"]
    assert _names(result) == ["Тверская улица, 7"]
    assert geocoder.nearby_calls == []


async def test_a_found_settlement_makes_the_text_search_needless(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = RichStubGeocoder(
        found=[moscow_house("Тверская улица", "7")],
        place=SUZDAL_PLACE,
        nearby=[suzdal()],
    )

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="суздаль")
    )

    assert geocoder.calls == []
    assert _names(result) == ["Кремлёвская улица, 6"]
    assert geocoder.place_nears == [None]


@pytest.mark.parametrize(
    "text",
    ["суздаль 5", "суздаль 5 улица ленина", "ул", "один два три четыре пять"],
)
async def test_a_text_that_cannot_be_a_settlement_is_not_looked_up(
    sessionmaker_: Maker, city_id: int, published: Published, text: str
) -> None:
    geocoder = RichStubGeocoder(found=[], place=SUZDAL_PLACE, nearby=[suzdal()])

    result = await _search(sessionmaker_, geocoder).search(SearchQueryDTO(query=text))

    assert geocoder.place_calls == []
    assert result.place is None


async def test_the_request_can_opt_out_of_the_settlement_lookup(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = RichStubGeocoder(found=[], place=SUZDAL_PLACE, nearby=[suzdal()])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="суздаль", external=False)
    )

    assert (geocoder.place_calls, result.place) == ([], None)


async def test_an_unknown_name_gives_no_place_and_no_houses_are_listed(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = RichStubGeocoder(found=[], place=None, nearby=[suzdal()])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="нигдеград")
    )

    assert (result.place, result.items) == (None, [])
    assert geocoder.nearby_calls == []
    assert result.external.state == "ok"


async def test_a_failing_settlement_lookup_leaves_the_answer_and_says_why(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = RichStubGeocoder(
        found=[],
        place_error=GeocoderError("HTTP 503"),
        error=GeocoderError("HTTP 503"),
    )

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="суздаль")
    )

    assert (result.place, result.items) == (None, [])
    assert result.external.state == "error"


async def test_the_settlement_is_found_even_when_the_map_is_far_away(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    geocoder = RichStubGeocoder(found=[], place=SUZDAL_PLACE, nearby=[suzdal()])

    result = await _search(sessionmaker_, geocoder).search(
        SearchQueryDTO(query="суздаль", near=NEAR)
    )

    assert _names(result) == ["Кремлёвская улица, 6"]
    assert result.place is not None
    assert geocoder.nearby_calls[0][0] == SUZDAL_CENTRE


async def test_nothing_farther_than_the_limit_is_around_a_point(
    sessionmaker_: Maker, city_id: int, published: Published
) -> None:
    await _near(sessionmaker_, "1", 0.30)
    geocoder = RichStubGeocoder(found=[], nearby=[])

    result = await _search(sessionmaker_, geocoder).search(SearchQueryDTO(near=NEAR))

    assert result.items == []
    assert len(geocoder.nearby_calls) == 1
