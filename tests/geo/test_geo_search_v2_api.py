from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from support.geocoder import StubGeocoder, moscow_house
from support.http import api_client, principal

from geo.service.external import ExternalSearch

BASE = "/geo/v2"
V1 = "/geo/v1"
ADMIN = principal(superuser=True)
USER = principal()


@pytest.fixture
def geocoder(monkeypatch: pytest.MonkeyPatch) -> StubGeocoder:
    stub = StubGeocoder([moscow_house()])
    external = ExternalSearch(stub)
    monkeypatch.setattr("geo.service.search.shared_external_search", lambda: external)
    return stub


@pytest.fixture
async def api(sessionmaker_: Any, published: Any) -> AsyncIterator[httpx.AsyncClient]:
    from geo.app.app import app

    async with api_client(app, sessionmaker_) as client:
        yield client


async def _address(
    api: httpx.AsyncClient, city_id: int, name: str, **extra: Any
) -> dict[str, Any]:
    response = await api.post(
        f"{V1}/addresses",
        json={"city_id": city_id, "name": name, **extra},
        headers=ADMIN,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_search_needs_a_token(api: httpx.AsyncClient) -> None:
    assert (
        await api.get(f"{BASE}/search", params={"q": "тверская"})
    ).status_code == 401


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"q": "   "},
        {"lat": 55.7},
        {"lon": 37.6},
        {"q": "тверская", "limit": 51},
        {"q": "тверская", "limit": 0},
        {"q": "тверская", "kinds": "city"},
        {"q": "тверская", "external": "always"},
        {"lat": 91, "lon": 37},
    ],
)
async def test_search_rejects_a_request_it_cannot_answer(
    api: httpx.AsyncClient, params: dict[str, Any]
) -> None:
    assert (
        await api.get(f"{BASE}/search", params=params, headers=USER)
    ).status_code == 422


async def test_results_carry_the_clean_name_and_the_city_line_separately(
    api: httpx.AsyncClient, city_id: int
) -> None:
    address = await _address(
        api, city_id, "Тверская улица, 7", spot={"lat": 55.7583, "lon": 37.6116}
    )
    location = await api.post(
        f"{V1}/locations",
        json={"name": "Актовый зал", "address_id": address["id"]},
        headers=ADMIN,
    )

    response = await api.get(
        f"{BASE}/search",
        params={"q": "тверская москва", "external": "off"},
        headers=USER,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["external"] == {"state": "skipped", "provider": None}
    kinds = {item["kind"]: item for item in body["items"]}
    hit = kinds["address"]["address"]
    assert (hit["name"], hit["locality"], hit["full_name"]) == (
        "Тверская улица, 7",
        "Москва, Россия",
        "Тверская улица, 7, Москва, Россия",
    )
    assert hit["map_uri"] == "geo:55.7583,37.6116"
    assert kinds["address"]["origin"] == "local"
    assert kinds["address"]["score"] > 0
    place = kinds["location"]["location"]
    assert place["id"] == location.json()["id"]
    assert (place["display_name"], place["locality"]) == (
        "Актовый зал",
        "Москва, Россия",
    )


async def test_kinds_and_the_city_filter_narrow_the_answer(
    api: httpx.AsyncClient, city_id: int
) -> None:
    address = await _address(api, city_id, "Тверская улица, 7")
    await api.post(
        f"{V1}/locations",
        json={"name": "Тверской зал", "address_id": address["id"]},
        headers=ADMIN,
    )

    only_locations = await api.get(
        f"{BASE}/search",
        params={"q": "тверская", "kinds": "location", "external": "off"},
        headers=USER,
    )
    other_city = await api.get(
        f"{BASE}/search",
        params={"q": "тверская", "city_id": city_id + 1, "external": "off"},
        headers=USER,
    )

    assert [i["kind"] for i in only_locations.json()["items"]] == ["location"]
    assert other_city.json()["items"] == []


async def test_a_point_without_text_lists_what_is_near(
    api: httpx.AsyncClient, city_id: int
) -> None:
    await _address(api, city_id, "Далеко", spot={"lat": 56.5, "lon": 37.6})
    await _address(api, city_id, "Рядом", spot={"lat": 55.7501, "lon": 37.6})

    response = await api.get(
        f"{BASE}/search", params={"lat": 55.75, "lon": 37.6}, headers=USER
    )

    assert [i["address"]["name"] for i in response.json()["items"]] == [
        "Рядом",
        "Далеко",
    ]
    assert {i["score"] for i in response.json()["items"]} == {None}


async def test_an_unknown_address_is_found_externally_and_stored(
    api: httpx.AsyncClient, city_id: int, geocoder: StubGeocoder
) -> None:
    response = await api.get(
        f"{BASE}/search", params={"q": "тверская 7 москва"}, headers=USER
    )
    body = response.json()

    [item] = body["items"]
    assert body["external"] == {"state": "ok", "provider": "stub"}
    assert item["origin"] == "external"
    assert item["address"]["source"] == "photon"
    stored = await api.get(f"{BASE}/addresses/{item['address']['id']}", headers=USER)
    assert stored.status_code == 200
    assert stored.json()["locality"] == "Москва, Россия"
    assert len(geocoder.calls) == 1


async def test_external_off_never_reaches_the_geocoder(
    api: httpx.AsyncClient, city_id: int, geocoder: StubGeocoder
) -> None:
    response = await api.get(
        f"{BASE}/search",
        params={"q": "тверская 7 москва", "external": "off"},
        headers=USER,
    )

    assert response.json() == {
        "items": [],
        "external": {"state": "skipped", "provider": None},
    }
    assert geocoder.calls == []


async def test_a_dead_geocoder_still_gets_a_200(
    api: httpx.AsyncClient, city_id: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    from geo.geocoder.base import GeocoderError

    external = ExternalSearch(StubGeocoder(error=GeocoderError("HTTP 503")))
    monkeypatch.setattr("geo.service.search.shared_external_search", lambda: external)

    response = await api.get(f"{BASE}/search", params={"q": "тверская 7"}, headers=USER)

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["external"]["state"] == "error"


async def test_v2_reads_an_address_and_a_location_with_the_city_line(
    api: httpx.AsyncClient, city_id: int
) -> None:
    address = await _address(api, city_id, "Мясницкая улица, 20")
    location = (
        await api.post(
            f"{V1}/locations",
            json={"name": "Актовый зал", "address_id": address["id"]},
            headers=ADMIN,
        )
    ).json()

    read_address = await api.get(f"{BASE}/addresses/{address['id']}", headers=USER)
    read_location = await api.get(f"{BASE}/locations/{location['id']}", headers=USER)

    assert read_address.json()["locality"] == "Москва, Россия"
    assert read_location.json()["address"]["locality"] == "Москва, Россия"
    assert read_location.json()["locality"] == "Москва, Россия"
    assert (
        await api.get(f"{BASE}/addresses/{uuid4()}", headers=USER)
    ).status_code == 404
    assert (
        await api.get(f"{BASE}/locations/{uuid4()}", headers=USER)
    ).status_code == 404


async def test_v1_keeps_its_shape(api: httpx.AsyncClient, city_id: int) -> None:
    address = await _address(api, city_id, "Мясницкая улица, 20")

    assert "locality" not in address
    assert "full_name" not in address
