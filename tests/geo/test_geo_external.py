import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from support.geocoder import (
    SUZDAL_PLACE,
    Clock,
    RichStubGeocoder,
    StubGeocoder,
    moscow_house,
)

from geo.dto.point import PointDTO
from geo.dto.point import PointDTO as Point
from geo.geocoder.base import (
    GeocodedAddress,
    GeocodedPlace,
    GeocoderError,
    RateLimitedError,
)
from geo.geocoder.photon import (
    PhotonGeocoder,
    names_street_near,
    parse_features,
    parse_import_date,
    pick_place,
)
from geo.service.external import ExternalSearch, shared_external_search

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


def _town(
    name: str = "Суздаль",
    *,
    osm_key: str = "place",
    osm_value: str = "town",
    state: str | None = "Владимирская область",
    extent: list[float] | None = None,
    lon: float = 40.4487893,
    lat: float = 56.4193908,
) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "osm_type": "N",
        "osm_id": 1,
        "osm_key": osm_key,
        "osm_value": osm_value,
        "type": "city",
        "name": name,
        "state": state,
        "country": "Россия",
        "extent": extent,
    }
    return {
        "type": "Feature",
        "properties": {k: v for k, v in properties.items() if v is not None},
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


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
        streets: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.payload = payload if payload is not None else _payload(_feature())
        self.streets = streets if streets is not None else _payload()
        self.status = status
        self.headers = headers
        self.delay = delay
        self.import_date = import_date
        self.queries: list[dict[str, str]] = []
        self.reverse_queries: list[dict[str, str]] = []

    async def handle(self, request: web.Request) -> web.Response:
        self.queries.append(dict(request.query))
        if self.delay:
            await asyncio.sleep(self.delay)
        if request.query.get("layer") == "street":
            return web.json_response(
                self.streets, status=self.status, headers=self.headers
            )
        return web.json_response(
            self.payload, status=self.status, headers=self.headers
        )

    async def handle_reverse(self, request: web.Request) -> web.Response:
        self.reverse_queries.append(dict(request.query))
        return web.json_response(
            self.payload, status=self.status, headers=self.headers
        )

    async def handle_status(self, request: web.Request) -> web.Response:
        body: dict[str, Any] = {"status": "Ok"}
        if self.import_date is not None:
            body["import_date"] = self.import_date
        return web.json_response(body, status=self.status, headers=self.headers)


@asynccontextmanager
async def serving(photon: FakePhoton):
    app = web.Application()
    app.router.add_get("/api", photon.handle)
    app.router.add_get("/status", photon.handle_status)
    app.router.add_get("/reverse", photon.handle_reverse)
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


SUZDAL_EXTENT = [40.4190217, 56.4554768, 40.4769505, 56.399337]


def test_a_town_is_read_with_its_region_point_and_box():
    place = pick_place("суздаль", _payload(_town(extent=SUZDAL_EXTENT)))

    assert place == GeocodedPlace(
        name="Суздаль",
        region="Владимирская область",
        country="Россия",
        lat=56.4193908,
        lon=40.4487893,
        bbox=(40.4190217, 56.399337, 40.4769505, 56.4554768),
    )


def test_a_town_without_a_box_has_none():
    place = pick_place("суздаль", _payload(_town()))

    assert place is not None
    assert place.bbox is None


@pytest.mark.parametrize(
    "typed, found",
    [
        ("Суздаль", "Суздаль"),
        ("ростов", "Ростов Великий"),
        ("ростов-на-дону", "Ростов-на-Дону"),
        ("Ростов на Дону", "Ростов-на-Дону"),
        ("пушкинские горы", "Пушкинские Горы"),
        ("ЧЁРНАЯ речка", "Черная речка"),
    ],
)
def test_the_typed_words_must_start_the_name_of_the_settlement(typed: str, found: str):
    place = pick_place(typed, _payload(_town(found)))

    assert place is not None and place.name == found


@pytest.mark.parametrize(
    "typed",
    [
        "горы",
        "суздальская",
        "ленина суздаль",
        "кремль",
        "суз",
        "суздал",
        "суздаль кремль",
    ],
)
def test_a_name_that_only_shares_a_word_is_not_the_place(typed: str):
    assert pick_place(typed, _payload(_town("Суздаль"))) is None


def test_the_first_matching_settlement_wins_over_a_later_better_spelling():
    payload = _payload(
        _town("Ростов Великий"), _town("Ростов", state="Сумська область")
    )

    place = pick_place("ростов", payload)

    assert place is not None and place.name == "Ростов Великий"


def test_a_boundary_a_street_or_a_shop_is_not_a_settlement():
    payload = _payload(
        _town(
            "городское поселение Суздаль",
            osm_key="boundary",
            osm_value="administrative",
        ),
        _town("Суздальская улица", osm_key="highway", osm_value="residential"),
    )

    assert pick_place("суздаль", payload) is None


def test_a_payload_that_is_not_a_feature_collection_is_an_error():
    with pytest.raises(GeocoderError):
        pick_place("суздаль", {"message": "rate limited"})


async def test_photon_looks_a_settlement_up_in_the_city_layer_only():
    photon = FakePhoton(_payload(_town(extent=SUZDAL_EXTENT)))
    async with serving(photon) as url:
        place = await PhotonGeocoder(url).place("суздаль", near=None)

    assert place is not None and place.name == "Суздаль"
    assert photon.queries == [{"q": "суздаль", "layer": "city", "limit": "5"}]


def _street(name: str, lon: float, lat: float) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {"osm_key": "highway", "osm_value": "residential", "name": name},
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


MOSCOW_POINT = Point(lat=55.7558, lon=37.6173)


async def test_a_word_that_is_a_street_near_the_map_is_not_a_settlement():
    photon = FakePhoton(
        _payload(_town("Тверская", state="Краснодарский край")),
        streets=_payload(_street("Тверская улица", 37.6, 55.76)),
    )
    async with serving(photon) as url:
        place = await PhotonGeocoder(url).place("тверская", near=MOSCOW_POINT)

    assert place is None
    assert [query["layer"] for query in photon.queries] == ["street"]
    assert photon.queries[0]["lat"] == "55.7558"


async def test_a_street_far_from_the_map_does_not_hide_the_settlement():
    photon = FakePhoton(
        _payload(_town("Суздаль")),
        streets=_payload(_street("Суздальская улица", 30.3, 59.9)),
    )
    async with serving(photon) as url:
        place = await PhotonGeocoder(url).place("суздаль", near=MOSCOW_POINT)

    assert place is not None and place.name == "Суздаль"
    assert [query["layer"] for query in photon.queries] == ["street", "city"]


@pytest.mark.parametrize(
    "typed, street, expected",
    [
        ("тверская", "Тверская улица", True),
        ("тверская", "улица Тверская", True),
        ("ленинградский проспект", "Ленинградский проспект", True),
        ("суздаль", "Суздальская улица", False),
        ("тверская", "Тверская-Ямская улица", True),
        ("ямская", "Тверская улица", False),
    ],
)
def test_a_street_is_named_by_whole_words_without_its_type(
    typed: str, street: str, expected: bool
):
    payload = _payload(_street(street, 37.6, 55.76))

    assert names_street_near(typed, MOSCOW_POINT, payload) is expected


def test_a_street_list_that_is_not_a_feature_collection_is_an_error():
    with pytest.raises(GeocoderError):
        names_street_near("тверская", MOSCOW_POINT, {"message": "x"})


def _house(
    street: str, housenumber: str | None, osm_id: int, **extra: Any
) -> dict[str, Any]:
    return _feature(
        street=street, housenumber=housenumber, osm_id=osm_id, osm_type="N", **extra
    )


async def test_photon_lists_the_houses_around_a_point_once_each_nearest_first():
    photon = FakePhoton(
        _payload(
            _house("Кремлёвская улица", "6", 1, name="Бар"),
            _house("Кремлёвская улица", "6", 2, name="Кафе"),
            _house("Кремлёвская улица", "9", 3),
            _house("улица Кремлёвская", "6", 4, name="Магазин"),
            _house("Ленина улица", None, 5),
            _house("Ленина улица", "7", 6),
        )
    )
    async with serving(photon) as url:
        found = await PhotonGeocoder(url).nearby(
            Point(lat=56.4185, lon=40.447), radius_km=2.0, limit=2
        )

    assert [(item.name, item.source_id) for item in found] == [
        ("Кремлёвская улица, 6", "node/1"),
        ("Кремлёвская улица, 9", "node/3"),
    ]
    assert photon.reverse_queries == [
        {
            "lat": "56.4185",
            "lon": "40.447",
            "layer": "house",
            "radius": "2.0",
            "limit": "12",
        }
    ]


async def test_the_overfetch_for_nearby_houses_is_capped():
    photon = FakePhoton(_payload())
    async with serving(photon) as url:
        await PhotonGeocoder(url).nearby(
            Point(lat=56.4, lon=40.4), radius_km=1.0, limit=40
        )

    assert photon.reverse_queries[0]["limit"] == "50"


async def test_a_failing_reverse_search_is_a_geocoder_error():
    async with serving(FakePhoton(status=503)) as url:
        with pytest.raises(GeocoderError):
            await PhotonGeocoder(url).nearby(
                Point(lat=56.4, lon=40.4), radius_km=1.0, limit=5
            )


class _Searches:
    name = "searches-only"

    async def search(
        self, query: str, *, near: Point | None, limit: int
    ) -> list[GeocodedAddress]:
        return []


async def test_nearby_and_place_are_cached_like_a_search():
    geocoder = RichStubGeocoder(
        found=[], nearby=[moscow_house()], place=SUZDAL_PLACE
    )
    external = ExternalSearch(geocoder, ttl=60.0, clock=(clock := Clock()))
    point = Point(lat=55.7512, lon=37.6001)

    first = await external.nearby(point, radius_km=2.0, limit=5)
    second = await external.nearby(
        Point(lat=55.7549, lon=37.6049), radius_km=2.0, limit=5
    )
    other_radius = await external.nearby(point, radius_km=5.0, limit=5)
    place = await external.place("Суздаль", near=None)
    again = await external.place("суздаль", near=None)
    clock.now += 61
    expired = await external.nearby(point, radius_km=2.0, limit=5)

    assert [o.state for o in (first, second, other_radius, expired)] == [
        "ok",
        "cached",
        "ok",
        "ok",
    ]
    assert (place.state, again.state, place.items) == ("ok", "cached", (SUZDAL_PLACE,))
    assert len(geocoder.nearby_calls) == 3
    assert geocoder.place_calls == ["Суздаль"]


async def test_a_place_that_does_not_exist_is_an_empty_ok_answer():
    external = ExternalSearch(RichStubGeocoder(found=[]))

    outcome = await external.place("ничего", near=None)

    assert (outcome.state, outcome.items) == ("ok", ())


async def test_a_geocoder_that_cannot_do_it_is_skipped_not_failed():
    external = ExternalSearch(_Searches())  # pyright: ignore[reportArgumentType]

    nearby = await external.nearby(Point(lat=1, lon=1), radius_km=1.0, limit=5)
    place = await external.place("суздаль", near=None)

    assert (nearby.state, place.state) == ("skipped", "skipped")
    assert external._failures == 0  # pyright: ignore[reportPrivateUsage]


async def test_the_breaker_counts_every_kind_of_request():
    geocoder = RichStubGeocoder(
        found=[],
        nearby_error=GeocoderError("HTTP 503"),
        place_error=GeocoderError("HTTP 503"),
        error=GeocoderError("HTTP 503"),
    )
    external = ExternalSearch(geocoder, failure_threshold=3, cooldown=30.0)

    states = [
        (await external.search("запрос", near=None, limit=5)).state,
        (await external.nearby(Point(lat=1, lon=1), radius_km=1.0, limit=5)).state,
        (await external.place("суздаль", near=None)).state,
        (await external.place("ростов", near=None)).state,
    ]

    assert states == ["error", "error", "error", "unavailable"]


async def test_a_burst_goes_through_and_the_budget_refills_with_time():
    geocoder, clock = StubGeocoder(), Clock()
    external = ExternalSearch(geocoder, rate=1.0, burst=3, clock=clock)

    spent = [
        (await external.search(f"запрос {n}", near=None, limit=5)).state
        for n in range(5)
    ]
    clock.now += 2
    refilled = [
        (await external.search(f"другой {n}", near=None, limit=5)).state
        for n in range(3)
    ]

    assert spent == ["ok", "ok", "ok", "throttled", "throttled"]
    assert refilled == ["ok", "ok", "throttled"]
    assert len(geocoder.calls) == 5


async def test_a_throttled_request_is_not_sent_and_is_not_a_failure():
    geocoder = StubGeocoder()
    external = ExternalSearch(
        geocoder, rate=0.001, burst=1, failure_threshold=1, clock=Clock()
    )

    await external.search("первый", near=None, limit=5)
    blocked = await external.search("второй", near=None, limit=5)
    cached = await external.search("первый", near=None, limit=5)

    assert (blocked.state, blocked.provider, blocked.items) == ("throttled", "stub", ())
    assert cached.state == "cached"
    assert len(geocoder.calls) == 1
    assert external._failures == 0  # pyright: ignore[reportPrivateUsage]


async def test_every_kind_of_request_spends_the_same_budget():
    geocoder = RichStubGeocoder(found=[], nearby=[moscow_house()], place=SUZDAL_PLACE)
    external = ExternalSearch(geocoder, rate=0.001, burst=2, clock=Clock())

    states = [
        (await external.nearby(Point(lat=1, lon=1), radius_km=1.0, limit=5)).state,
        (await external.place("суздаль", near=None)).state,
        (await external.search("запрос", near=None, limit=5)).state,
    ]

    assert states == ["ok", "ok", "throttled"]


async def test_no_rate_means_no_limit():
    geocoder = StubGeocoder()
    external = ExternalSearch(geocoder, clock=Clock())

    states = {
        (await external.search(f"запрос {n}", near=None, limit=5)).state
        for n in range(50)
    }

    assert states == {"ok"}


async def test_photon_reports_how_long_it_asks_to_wait():
    photon = FakePhoton(status=429, headers={"Retry-After": "120"})
    async with serving(photon) as url:
        with pytest.raises(RateLimitedError) as caught:
            await PhotonGeocoder(url).search("тверская", near=None, limit=5)

    assert caught.value.retry_after == 120.0


@pytest.mark.parametrize(
    "header", [None, "soon", "-5", "Wed, 21 Oct 2026 07:28:00 GMT"]
)
async def test_a_429_without_a_usable_pause_still_is_rate_limited(header: str | None):
    photon = FakePhoton(
        status=429, headers={"Retry-After": header} if header is not None else None
    )
    async with serving(photon) as url:
        with pytest.raises(RateLimitedError) as caught:
            await PhotonGeocoder(url).search("тверская", near=None, limit=5)

    assert caught.value.retry_after is None


async def test_a_429_stops_every_request_for_as_long_as_the_provider_asked():
    geocoder, clock = StubGeocoder(error=RateLimitedError("HTTP 429", 120.0)), Clock()
    external = ExternalSearch(geocoder, cooldown=30.0, clock=clock)

    first = await external.search("первый", near=None, limit=5)
    during = await external.search("второй", near=None, limit=5)
    clock.now += 119
    still = await external.search("третий", near=None, limit=5)
    clock.now += 2
    geocoder.error = None
    after = await external.search("четвёртый", near=None, limit=5)

    assert [first.state, during.state, still.state, after.state] == [
        "throttled",
        "unavailable",
        "unavailable",
        "ok",
    ]
    assert len(geocoder.calls) == 2


@pytest.mark.parametrize(
    ("asked", "paused"), [(None, 60.0), (5.0, 30.0), (86_400.0, 900.0)]
)
async def test_the_pause_after_a_429_is_kept_within_sane_bounds(
    asked: float | None, paused: float
):
    geocoder, clock = StubGeocoder(error=RateLimitedError("HTTP 429", asked)), Clock()
    external = ExternalSearch(geocoder, cooldown=30.0, clock=clock)

    await external.search("первый", near=None, limit=5)
    clock.now += paused - 1
    held = await external.search("второй", near=None, limit=5)
    clock.now += 2
    geocoder.error = None
    released = await external.search("третий", near=None, limit=5)

    assert (held.state, released.state) == ("unavailable", "ok")


def test_the_shared_search_takes_its_budget_from_the_settings(
    monkeypatch: pytest.MonkeyPatch,
):
    from core.config.settings import settings

    monkeypatch.setattr("geo.service.external._shared", None)
    monkeypatch.setattr(settings, "GEO_EXTERNAL_SEARCH", True)
    monkeypatch.setattr(settings, "GEO_EXTERNAL_RATE", 0.5)
    monkeypatch.setattr(settings, "GEO_EXTERNAL_BURST", 4)

    shared = shared_external_search()

    assert shared is not None
    assert (shared.rate, shared.burst) == (0.5, 4)
