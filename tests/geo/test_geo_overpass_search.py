# ruff: noqa: RUF001
from contextlib import asynccontextmanager
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from geo.bootstrap.sources import OverpassSource
from geo.dto.point import PointDTO
from geo.geocoder.base import GeocoderError
from geo.geocoder.overpass import OverpassGeocoder

NEAR = PointDTO(lat=55.7583, lon=37.6116)


Element = dict[str, Any]


def _node(node_id: int, street: str, house: str, lat: float, lon: float) -> Element:
    return {
        "type": "node",
        "id": node_id,
        "lat": lat,
        "lon": lon,
        "tags": {"addr:street": street, "addr:housenumber": house},
    }


def _way(way_id: int, street: str, house: str, lat: float, lon: float) -> Element:
    return {
        "type": "way",
        "id": way_id,
        "center": {"lat": lat, "lon": lon},
        "tags": {"addr:street": street, "addr:housenumber": house},
    }


class FakeOverpass:
    def __init__(self, *elements: dict[str, Any], status: int = 200):
        self.elements = list(elements)
        self.status = status
        self.queries: list[str] = []

    async def handle(self, request: web.Request) -> web.Response:
        body = await request.post()
        self.queries.append(str(body["data"]))
        return web.json_response({"elements": self.elements}, status=self.status)


@asynccontextmanager
async def serving(overpass: FakeOverpass):
    app = web.Application()
    app.router.add_post("/api", overpass.handle)
    server = TestServer(app)
    await server.start_server()
    try:
        yield OverpassSource(
            urls=[f"http://{server.host}:{server.port}/api"],  # pyright: ignore[reportUnknownMemberType]
            timeout=5,
            attempts=1,
            cooldown=0.01,
        )
    finally:
        await server.close()


async def test_the_query_asks_for_the_street_stem_and_house_digits_near_the_point():
    overpass = FakeOverpass()
    async with serving(overpass) as source:
        found = await OverpassGeocoder(source).search("тверская 7", near=NEAR, limit=5)

    [query] = overpass.queries
    assert found == []
    assert '["addr:street"~"тверск",i]' in query
    assert '["addr:housenumber"~"^7([^0-9]|$)"]' in query
    assert "out center 15;" in query


async def test_words_after_the_house_number_name_the_city_and_are_not_searched():
    overpass = FakeOverpass()
    async with serving(overpass) as source:
        await OverpassGeocoder(source).search(
            "улица Тверская 7 москва", near=NEAR, limit=5
        )

    [query] = overpass.queries
    assert query.count('["addr:street"~') == 2
    assert "москва" not in query.casefold().replace("тверск", "")


async def test_only_the_named_house_is_kept_and_the_nearest_comes_first():
    overpass = FakeOverpass(
        _node(1, "Тверская улица", "7", 55.7600, 37.6116),
        _way(2, "Тверская улица", "7", 55.7585, 37.6116),
        _node(3, "Тверская улица", "7А", 55.7584, 37.6116),
        _node(4, "Тверская улица", "70", 55.7583, 37.6116),
        _node(5, "Тверская улица", "7 к1", 55.7583, 37.6117),
    )
    async with serving(overpass) as source:
        found = await OverpassGeocoder(source).search(
            "тверская 7", near=NEAR, limit=5
        )

    assert [(item.source_id, item.name) for item in found] == [
        ("way/2", "Тверская улица, 7"),
        ("node/1", "Тверская улица, 7"),
    ]


async def test_a_street_named_in_full_outranks_a_nearer_street_with_the_same_stem():
    overpass = FakeOverpass(
        _node(1, "Тверской бульвар", "7", 55.7584, 37.6116),
        _way(2, "1-я Тверская-Ямская улица", "7", 55.7584, 37.6117),
        _node(3, "Тверская улица", "7", 55.7650, 37.6116),
    )
    async with serving(overpass) as source:
        found = await OverpassGeocoder(source).search("тверская 7", near=NEAR, limit=5)

    assert [item.source_id for item in found] == ["node/3", "node/1", "way/2"]


async def test_a_hit_carries_no_city_and_is_called_osm():
    overpass = FakeOverpass(_node(1, "Тверская улица", "7", 55.7585, 37.6116))
    async with serving(overpass) as source:
        [item] = await OverpassGeocoder(source).search("тверская 7", near=NEAR, limit=5)

    assert (item.city, item.region, item.country) == ("", "", "")
    assert (item.source, item.placed) == ("osm", False)


async def test_without_a_street_or_a_point_nothing_is_asked():
    overpass = FakeOverpass()
    async with serving(overpass) as source:
        geocoder = OverpassGeocoder(source)
        no_point = await geocoder.search("тверская 7", near=None, limit=5)
        no_street = await geocoder.search("7", near=NEAR, limit=5)
        only_type = await geocoder.search("улица 7", near=NEAR, limit=5)

    assert (no_point, no_street, only_type) == ([], [], [])
    assert overpass.queries == []


async def test_an_overpass_failure_is_a_geocoder_error():
    async with serving(FakeOverpass(status=400)) as source:
        with pytest.raises(GeocoderError):
            await OverpassGeocoder(source).search("тверская 7", near=NEAR, limit=5)


@pytest.mark.parametrize("word", ['тверская"', "а]|b", "a;b", "тверская ул"])
async def test_a_street_word_that_could_change_the_query_is_refused(word: str):
    overpass = FakeOverpass()
    async with serving(overpass) as source:
        with pytest.raises(ValueError, match="letters, digits and hyphens"):
            await source.search((55.0, 37.0, 56.0, 38.0), [word], None, 5)

    assert overpass.queries == []


async def test_a_house_filter_that_is_not_digits_is_refused():
    overpass = FakeOverpass()
    async with serving(overpass) as source:
        with pytest.raises(ValueError, match="digits only"):
            await source.search((55.0, 37.0, 56.0, 38.0), ["тверск"], '7"]', 5)

    assert overpass.queries == []
