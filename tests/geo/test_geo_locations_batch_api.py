from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from support.http import api_client, principal

V2 = "/geo/v2/locations"
USER = principal()


@pytest.fixture
async def api(sessionmaker_: Any, published: Any) -> AsyncIterator[httpx.AsyncClient]:
    from geo.app.app import app

    async with api_client(app, sessionmaker_) as client:
        yield client


async def _location(api: httpx.AsyncClient, name: str) -> str:
    response = await api.post(V2, json={"name": name}, headers=USER)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _ids(*ids: str) -> dict[str, list[str]]:
    return {"id": list(ids)}


async def test_reading_many_needs_a_token(api: httpx.AsyncClient) -> None:
    assert (await api.get(V2, params=_ids(str(uuid4())))).status_code == 401


async def test_locations_come_in_the_order_of_the_ids(api: httpx.AsyncClient) -> None:
    first = await _location(api, "Hall, Kazan")
    second = await _location(api, "Park, Kazan")
    third = await _location(api, "Club, Kazan")

    response = await api.get(V2, params=_ids(third, first, second), headers=USER)

    assert response.status_code == 200, response.text
    assert [i["id"] for i in response.json()] == [third, first, second]
    assert [i["display_name"] for i in response.json()] == [
        "Club, Kazan",
        "Hall, Kazan",
        "Park, Kazan",
    ]


async def test_an_unknown_or_repeated_id_is_left_out(api: httpx.AsyncClient) -> None:
    known = await _location(api, "Hall, Kazan")

    response = await api.get(
        V2, params=_ids(str(uuid4()), known, known), headers=USER
    )

    assert response.status_code == 200
    assert [i["id"] for i in response.json()] == [known]


@pytest.mark.parametrize(
    "params",
    [
        {},
        _ids("not-a-uuid"),
        _ids(*[str(uuid4()) for _ in range(51)]),
    ],
)
async def test_the_ids_are_validated(
    api: httpx.AsyncClient, params: dict[str, list[str]]
) -> None:
    response = await api.get(V2, params=params, headers=USER)

    assert response.status_code == 422
