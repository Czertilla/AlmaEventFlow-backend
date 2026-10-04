from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from support.http import api_client, principal

BASE = "/geo/v1"
ADMIN = principal(superuser=True)
USER = principal()


@pytest.fixture
async def api(sessionmaker_: Any, published: Any) -> AsyncIterator[httpx.AsyncClient]:
    from geo.app.app import app

    async with api_client(app, sessionmaker_) as client:
        yield client


async def _address(
    api: httpx.AsyncClient, city_id: int, name: str, **extra: Any
) -> dict[str, Any]:
    response = await api.post(
        f"{BASE}/addresses",
        json={"city_id": city_id, "name": name, **extra},
        headers=ADMIN,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_addresses_and_locations_expose_timestamps(
    api: httpx.AsyncClient, city_id: int
) -> None:
    address = await _address(api, city_id, "Арбат, 10")
    location = await api.post(
        f"{BASE}/locations",
        json={"name": "Зал", "address_id": address["id"]},
        headers=ADMIN,
    )
    patched = await api.patch(
        f"{BASE}/locations/{location.json()['id']}",
        json={"name": "Большой зал"},
        headers=ADMIN,
    )

    assert address["created_at"]
    assert address["edited_at"] is None
    assert location.json()["created_at"]
    assert patched.json()["edited_at"] is not None


async def test_addresses_are_filtered_and_sorted(
    api: httpx.AsyncClient, city_id: int
) -> None:
    await _address(api, city_id, "Арбат, 10", spot={"lat": 55.75, "lon": 37.6})
    await _address(api, city_id, "Бульварное кольцо, 1")

    with_spot = await api.get(
        f"{BASE}/addresses", params={"spot__isnull": False}, headers=USER
    )
    without_spot = await api.get(
        f"{BASE}/addresses", params={"spot__isnull": True}, headers=USER
    )
    newest = await api.get(
        f"{BASE}/addresses", params={"order_by": "-created_at"}, headers=USER
    )
    several_cities = await api.get(
        f"{BASE}/addresses", params={"city_id__in": f"{city_id},999"}, headers=USER
    )
    bad_order = await api.get(
        f"{BASE}/addresses", params={"order_by": "source_id"}, headers=USER
    )

    assert [a["name"] for a in with_spot.json()["items"]] == ["Арбат, 10"]
    assert [a["name"] for a in without_spot.json()["items"]] == ["Бульварное кольцо, 1"]
    assert newest.json()["items"][0]["name"] == "Бульварное кольцо, 1"
    assert several_cities.json()["pagination"]["total"] == 2
    assert bad_order.status_code == 422


async def test_locations_are_filtered_by_their_anchor(
    api: httpx.AsyncClient, city_id: int
) -> None:
    address = await _address(api, city_id, "Арбат, 10")
    await api.post(
        f"{BASE}/locations",
        json={"name": "Зал", "address_id": address["id"]},
        headers=ADMIN,
    )
    await api.post(
        f"{BASE}/locations",
        json={"name": "Площадка", "spot": {"lat": 55.0, "lon": 37.0}},
        headers=ADMIN,
    )

    anchored = await api.get(
        f"{BASE}/locations", params={"spot__isnull": True}, headers=USER
    )
    by_address = await api.get(
        f"{BASE}/locations", params={"address_id__in": address["id"]}, headers=USER
    )

    assert [loc["name"] for loc in anchored.json()["items"]] == ["Зал"]
    assert [loc["name"] for loc in by_address.json()["items"]] == ["Зал"]
