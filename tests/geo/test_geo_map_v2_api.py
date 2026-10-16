from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from support.http import api_client, principal

BASE = "/geo/v2/map"
V1 = "/geo/v1"
ADMIN = principal(superuser=True)
USER = principal()
WINDOW = "36.6,55.2,38.6,56.2"


@pytest.fixture
async def api(sessionmaker_: Any, published: Any) -> AsyncIterator[httpx.AsyncClient]:
    from geo.app.app import app

    async with api_client(app, sessionmaker_) as client:
        yield client


async def _address(
    api: httpx.AsyncClient, city_id: int, name: str, lat: float, lon: float
) -> dict[str, Any]:
    response = await api.post(
        f"{V1}/addresses",
        json={"city_id": city_id, "name": name, "spot": {"lat": lat, "lon": lon}},
        headers=ADMIN,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_the_map_needs_a_token(api: httpx.AsyncClient) -> None:
    assert (await api.get(BASE, params={"bbox": WINDOW, "zoom": 9})).status_code == 401


@pytest.mark.parametrize(
    "params",
    [
        {"zoom": 9},
        {"bbox": WINDOW},
        {"bbox": "1,2,3", "zoom": 9},
        {"bbox": "a,b,c,d", "zoom": 9},
        {"bbox": "36,55,181,56", "zoom": 9},
        {"bbox": "36,56,37,55", "zoom": 9},
        {"bbox": "36,-91,37,55", "zoom": 9},
        {"bbox": WINDOW, "zoom": -1},
        {"bbox": WINDOW, "zoom": 23},
        {"bbox": WINDOW, "zoom": 9, "radius_px": 10},
        {"bbox": WINDOW, "zoom": 9, "limit": 0},
        {"bbox": WINDOW, "zoom": 9, "kinds": "city"},
    ],
)
async def test_a_malformed_window_is_a_422(
    api: httpx.AsyncClient, params: dict[str, Any]
) -> None:
    assert (await api.get(BASE, params=params, headers=USER)).status_code == 422


async def test_the_window_comes_back_as_a_geojson_feature_collection(
    api: httpx.AsyncClient, city_id: int
) -> None:
    lone = await _address(api, city_id, "Арбат, 10", 55.7522, 37.5921)
    for index in range(3):
        await _address(api, city_id, f"Тверская, {index}", 55.9 + 0.00001 * index, 38.1)

    response = await api.get(BASE, params={"bbox": WINDOW, "zoom": 9}, headers=USER)
    body = response.json()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/geo+json")
    assert body["type"] == "FeatureCollection"
    assert (body["number_matched"], body["number_returned"], body["truncated"]) == (
        4,
        2,
        False,
    )
    cluster, entity = body["features"]
    assert cluster["type"] == entity["type"] == "Feature"
    assert cluster["properties"]["cluster"] is True
    assert cluster["properties"]["point_count"] == 3
    assert cluster["properties"]["counts"] == {"address": 3, "location": 0}
    assert cluster["geometry"] == {
        "type": "Point",
        "coordinates": pytest.approx(
            [
                38.1,
                55.9,
            ],
            abs=1e-3,
        ),
    }
    west, south, east, north = cluster["properties"]["bbox"]
    assert (west, east) == (38.1, 38.1) and south < north
    assert entity["id"] == lone["id"]
    assert entity["geometry"]["coordinates"] == [37.5921, 55.7522]
    assert entity["properties"] == {
        "cluster": False,
        "kind": "address",
        "name": "Арбат, 10",
        "locality": "Москва, Россия",
    }


async def test_kinds_and_limit_are_honoured(
    api: httpx.AsyncClient, city_id: int
) -> None:
    await _address(api, city_id, "Арбат, 10", 55.7522, 37.5921)
    await _address(api, city_id, "Тверская, 1", 55.9, 38.1)

    none_of_them = await api.get(
        BASE, params={"bbox": WINDOW, "zoom": 12, "kinds": "location"}, headers=USER
    )
    cut = await api.get(
        BASE, params={"bbox": WINDOW, "zoom": 12, "limit": 1}, headers=USER
    )

    assert none_of_them.json()["features"] == []
    assert (cut.json()["number_returned"], cut.json()["truncated"]) == (1, True)


async def test_a_window_across_the_antimeridian_is_accepted(
    api: httpx.AsyncClient, city_id: int
) -> None:
    await _address(api, city_id, "Эгвекинот, 1", 66.3, -179.9)

    response = await api.get(
        BASE, params={"bbox": "179,65,-179,67", "zoom": 9}, headers=USER
    )

    assert response.json()["number_matched"] == 1
