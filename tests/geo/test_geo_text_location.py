from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from support.geocoder import Maker, Published, count_rows
from support.http import api_client, principal

from geo.models.location import LocationORM

V1 = "/geo/v1/locations"
V2 = "/geo/v2/locations"
USER = principal()
TEXT = "ул. Пушкина, 10, ауд. 304, Казань"


@pytest.fixture
async def api(sessionmaker_: Any, published: Any) -> AsyncIterator[httpx.AsyncClient]:
    from geo.app.app import app

    async with api_client(app, sessionmaker_) as client:
        yield client


async def _create(api: httpx.AsyncClient, **body: Any) -> httpx.Response:
    return await api.post(V2, json=body, headers=USER)


def _created(published: Published) -> list[Any]:
    return [payload for name, payload in published if name == "on_location_created"]


async def test_creating_needs_a_token(api: httpx.AsyncClient) -> None:
    assert (await api.post(V2, json={"name": TEXT})).status_code == 401


async def test_a_location_can_be_nothing_but_a_name(
    api: httpx.AsyncClient, published: Published, sessionmaker_: Maker
) -> None:
    response = await _create(api, name=f"  {TEXT}  ")

    body = response.json()
    assert response.status_code == 200, response.text
    assert (body["name"], body["display_name"]) == (TEXT, TEXT)
    assert (body["spot"], body["address"], body["address_id"]) == (None, None, None)
    assert (body["map_uri"], body["locality"]) == (None, None)
    assert [[item.name for item in batch] for batch in _created(published)] == [[TEXT]]
    assert await count_rows(sessionmaker_, LocationORM) == 1


async def test_the_same_text_is_the_same_location_not_a_twin(
    api: httpx.AsyncClient, published: Published, sessionmaker_: Maker
) -> None:
    first = (await _create(api, name=TEXT)).json()
    respelled = f"  {TEXT.upper()}  ".replace(", ", ",   ")
    second = (await _create(api, name=respelled)).json()
    other = (await _create(api, name="ул. Ленина, 1, Казань")).json()

    assert second["id"] == first["id"]
    assert other["id"] != first["id"]
    assert len(_created(published)) == 2
    assert await count_rows(sessionmaker_, LocationORM) == 2


async def test_a_name_on_a_map_point_is_not_taken_for_the_text(
    api: httpx.AsyncClient, sessionmaker_: Maker
) -> None:
    pinned = (await _create(api, name=TEXT, spot={"lat": 55.79, "lon": 49.12})).json()
    text = (await _create(api, name=TEXT)).json()

    assert text["id"] != pinned["id"]
    assert await count_rows(sessionmaker_, LocationORM) == 2


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": "   "},
        {"name": "x" * 513},
        {"address_id": None, "spot": None},
        {
            "spot": {"lat": 55.7, "lon": 37.6},
            "address_id": "6f1c1bb2-0c52-4a4f-b6f8-3a3e9d2f4b11",
        },
    ],
)
async def test_what_cannot_be_placed_is_refused(
    api: httpx.AsyncClient, body: dict[str, Any]
) -> None:
    assert (await _create(api, **body)).status_code == 422


async def test_the_other_anchors_still_work_through_v2(
    api: httpx.AsyncClient,
) -> None:
    response = await _create(api, name="Двор", spot={"lat": 55.7, "lon": 37.6})

    body = response.json()
    assert response.status_code == 200, response.text
    assert body["map_uri"] == "geo:55.7,37.6"


async def test_v1_still_refuses_a_name_alone(api: httpx.AsyncClient) -> None:
    response = await api.post(V1, json={"name": TEXT}, headers=USER)

    assert response.status_code == 422


async def test_v1_reads_a_text_location_by_its_name(api: httpx.AsyncClient) -> None:
    created = (await _create(api, name=TEXT)).json()

    one = await api.get(f"{V1}/{created['id']}", headers=USER)
    listed = await api.get(V1, params={"search": "пушкина"}, headers=USER)

    assert one.status_code == 200
    assert one.json()["name"] == TEXT
    assert [item["id"] for item in listed.json()["items"]] == [created["id"]]


async def test_search_finds_a_text_location_by_its_words(
    api: httpx.AsyncClient,
) -> None:
    created = (await _create(api, name=TEXT)).json()

    found = await api.get(
        "/geo/v2/search",
        params={"q": "пушкина 10 казань", "external": "off"},
        headers=USER,
    )

    assert [(hit["kind"], hit["location"]["id"]) for hit in found.json()["items"]] == [
        ("location", created["id"])
    ]


async def test_a_text_location_is_not_around_a_point(api: httpx.AsyncClient) -> None:
    await _create(api, name=TEXT)

    around = await api.get(
        "/geo/v2/search",
        params={"lat": 55.79, "lon": 49.12, "external": "off"},
        headers=USER,
    )

    assert around.json()["items"] == []
