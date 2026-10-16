import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from support.geocoder import Clock, StubGeocoder

from geo.dto.point import PointDTO
from geo.geocoder.base import GeocodedAddress, GeocoderError
from geo.geocoder.photon import PhotonGeocoder, parse_features, parse_import_date
from geo.service.external import ExternalSearch

BUILT = datetime(2026, 10, 10, 22, 59, 51, tzinfo=UTC)


def _feature(**properties: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "osm_type": "R",
        "osm_id": 451292,
        "osm_key": "building",
        "osm_value": "commercial",
        "type": "house",
        "housenumber": "7",
        "name": "Центральный телеграф",
        "street": "Тверская улица",
        "district": "Тверской",
        "city": "Москва",
        "state": "Москва",
        "country": "Россия",
        "countrycode": "RU",
    }
    base.update(properties)
    return {
        "type": "Feature",
        "properties": {k: v for k, v in base.items() if v is not None},
        "geometry": {"type": "Point", "coordinates": [37.6116443, 55.7583099]},
    }


def _payload(*features: dict[str, Any]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


def test_parse_keeps_a_house_with_its_street_city_and_region():
    [address] = parse_features(_payload(_feature()))

    assert address == GeocodedAddress(
        source_id="relation/451292",
        street="Тверская улица",
        housenumber="7",
        lat=55.7583099,
        lon=37.6116443,
        city="Москва",
        region="Москва",
        country="Россия",
    )
    assert address.name == "Тверская улица, 7"


def test_parse_maps_every_osm_element_type():
    found = parse_features(
        _payload(
            _feature(osm_type="N", osm_id=1),
            _feature(osm_type="W", osm_id=2),
            _feature(osm_type="R", osm_id=3),
        )
    )

    assert [item.source_id for item in found] == ["node/1", "way/2", "relation/3"]


@pytest.mark.parametrize(
    "properties",
    [
        {"housenumber": None},
        {"street": None},
        {"city": None},
        {"country": None},
        {"osm_type": "X"},
        {"city": "Рахьинское городское поселение"},
        {"city": "городской округ Казань"},
    ],
)
def test_parse_drops_what_cannot_become_an_address_row(properties: dict[str, Any]):
    assert parse_features(_payload(_feature(**properties))) == []


def test_parse_falls_back_to_the_country_when_there_is_no_state():
    [address] = parse_features(_payload(_feature(state=None, country="Монако")))

    assert address.region == "Монако"


def test_parse_rejects_a_payload_that_is_not_a_feature_collection():
    with pytest.raises(GeocoderError):
        parse_features({"message": "rate limited"})


class FakePhoton:
    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        *,
        status: int = 200,
        delay: float = 0.0,
        import_date: str | None = "2026-10-10T22:59:51Z",
    ):
        self.payload = payload if payload is not None else _payload(_feature())
        self.status = status
        self.delay = delay
        self.import_date = import_date
        self.queries: list[dict[str, str]] = []

    async def handle(self, request: web.Request) -> web.Response:
        self.queries.append(dict(request.query))
        if self.delay:
            await asyncio.sleep(self.delay)
        return web.json_response(self.payload, status=self.status)

    async def handle_status(self, request: web.Request) -> web.Response:
        body: dict[str, Any] = {"status": "Ok"}
        if self.import_date is not None:
            body["import_date"] = self.import_date
        return web.json_response(body, status=self.status)


@asynccontextmanager
async def serving(photon: FakePhoton):
    app = web.Application()
    app.router.add_get("/api", photon.handle)
    app.router.add_get("/status", photon.handle_status)
    server = TestServer(app)
    await server.start_server()
    try:
        yield f"http://{server.host}:{server.port}"  # pyright: ignore[reportUnknownMemberType]
    finally:
        await server.close()


async def test_photon_asks_for_houses_and_biases_towards_the_point():
    photon = FakePhoton()
    async with serving(photon) as url:
        found = await PhotonGeocoder(url).search(
            "тверская 7", near=PointDTO(lat=55.75, lon=37.6), limit=5
        )

    assert [item.name for item in found] == ["Тверская улица, 7"]
    assert photon.queries == [
        {
            "q": "тверская 7",
            "layer": "house",
            "limit": "5",
            "lat": "55.75",
            "lon": "37.6",
        }
    ]


async def test_photon_turns_http_errors_and_timeouts_into_geocoder_errors():
    async with serving(FakePhoton(status=503)) as url:
        with pytest.raises(GeocoderError):
            await PhotonGeocoder(url).search("тверская", near=None, limit=5)

    async with serving(FakePhoton(delay=1.0)) as url:
        with pytest.raises(TimeoutError):
            await PhotonGeocoder(url, timeout=0.1).search(
                "тверская", near=None, limit=5
            )


async def test_photon_reports_when_its_data_was_built():
    async with serving(FakePhoton()) as url:
        built = await PhotonGeocoder(url).imported_at()
    async with serving(FakePhoton(import_date=None)) as url:
        unknown = await PhotonGeocoder(url).imported_at()
    async with serving(FakePhoton(status=503)) as url:
        with pytest.raises(GeocoderError):
            await PhotonGeocoder(url).imported_at()

    assert built == BUILT
    assert unknown is None


@pytest.mark.parametrize(
    "payload, expected",
    [
        ({"import_date": "2026-10-10T22:59:51Z"}, BUILT),
        ({"import_date": "2026-10-10T22:59:51"}, BUILT),
        ({"import_date": "yesterday"}, None),
        ({"import_date": 5}, None),
        ({}, None),
        ([], None),
    ],
)
def test_an_import_date_is_read_as_utc_or_not_at_all(
    payload: Any, expected: datetime | None
):
    assert parse_import_date(payload) == expected


async def test_a_repeated_query_is_served_from_the_cache_until_it_expires():
    geocoder, clock = StubGeocoder(), Clock()
    external = ExternalSearch(geocoder, ttl=60.0, clock=clock)
    near = PointDTO(lat=55.7512, lon=37.6001)

    first = await external.search("Тверская  7", near=near, limit=5)
    second = await external.search(
        "тверская 7", near=PointDTO(lat=55.7549, lon=37.6049), limit=5
    )
    clock.now += 61
    third = await external.search("тверская 7", near=near, limit=5)

    assert [first.state, second.state, third.state] == ["ok", "cached", "ok"]
    assert len(geocoder.calls) == 2
    assert second.items == first.items


async def test_the_cache_keeps_only_the_most_recent_queries():
    geocoder = StubGeocoder()
    external = ExternalSearch(geocoder, cache_size=2)

    for query in ("тверская", "мясницкая", "покровка"):
        await external.search(query, near=None, limit=5)
    states = [
        (await external.search(q, near=None, limit=5)).state
        for q in ("покровка", "тверская")
    ]

    assert states == ["cached", "ok"]


async def test_a_slow_provider_becomes_a_timeout_state():
    external = ExternalSearch(StubGeocoder(delay=1.0), timeout=0.05)

    outcome = await external.search("тверская", near=None, limit=5)

    assert (outcome.state, outcome.provider, outcome.items) == ("timeout", "stub", ())


async def test_the_breaker_stops_calling_a_failing_provider_until_the_cooldown_ends():
    geocoder, clock = StubGeocoder(error=GeocoderError("HTTP 503")), Clock()
    external = ExternalSearch(geocoder, failure_threshold=3, cooldown=30.0, clock=clock)

    states = [
        (await external.search(f"запрос {n}", near=None, limit=5)).state
        for n in range(5)
    ]
    clock.now += 31
    recovered = await external.search("запрос 9", near=None, limit=5)

    assert states == ["error", "error", "error", "unavailable", "unavailable"]
    assert len(geocoder.calls) == 4
    assert recovered.state == "error"


async def test_a_success_resets_the_failure_count():
    geocoder = StubGeocoder(error=GeocoderError("HTTP 503"))
    external = ExternalSearch(geocoder, failure_threshold=3)

    await external.search("первый запрос", near=None, limit=5)
    await external.search("второй запрос", near=None, limit=5)
    geocoder.error = None
    await external.search("третий запрос", near=None, limit=5)
    geocoder.error = GeocoderError("HTTP 503")
    states = [
        (await external.search(f"запрос {n}", near=None, limit=5)).state
        for n in range(3)
    ]

    assert states == ["error", "error", "error"]
