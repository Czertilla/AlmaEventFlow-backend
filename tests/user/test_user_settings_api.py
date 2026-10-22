import asyncio
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from user.service.settings import MAX_SETTINGS_BYTES, merge_settings

PASSWORD = "S3cret-pass"
URL = "/user/v2/users/me/settings"


async def _account(
    client: httpx.AsyncClient,
    engine: AsyncEngine,
    email: str = "ann@example.com",
    username: str = "ann",
) -> dict[str, str]:
    created = await client.post(
        "/user/v1/auth/register",
        json={"email": email, "password": PASSWORD, "username": username},
    )
    assert created.status_code == 201, created.text
    async with engine.begin() as conn:
        await conn.execute(
            text('UPDATE "user" SET is_verified = true WHERE email = :email'),
            {"email": email},
        )
    login = await client.post(
        "/user/v1/auth/jwt/login", data={"username": email, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def _patch(
    client: httpx.AsyncClient, headers: dict[str, str], values: dict[str, Any]
) -> httpx.Response:
    return await client.patch(URL, json={"values": values}, headers=headers)


def test_merge_sets_replaces_and_removes_top_level_keys() -> None:
    current = {"theme": "dark", "showHints": True, "nested": {"a": 1}}

    merged = merge_settings(
        current, {"theme": "light", "showHints": None, "nested": {"b": 2}, "x": 0}
    )

    assert merged == {"theme": "light", "nested": {"b": 2}, "x": 0}
    assert current == {"theme": "dark", "showHints": True, "nested": {"a": 1}}


def test_merge_ignores_removing_a_missing_key() -> None:
    assert merge_settings({"a": 1}, {"b": None}) == {"a": 1}


async def test_settings_require_authentication(client: httpx.AsyncClient) -> None:
    assert (await client.get(URL)).status_code == 401
    assert (await client.patch(URL, json={"values": {}})).status_code == 401


async def test_a_new_account_has_no_settings(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)

    response = await client.get(URL, headers=headers)

    assert response.status_code == 200, response.text
    assert response.json() == {"values": {}, "revision": 0, "edited_at": None}


async def test_patch_merges_and_bumps_the_revision(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)

    first = await _patch(client, headers, {"theme": "dark", "showHints": False})
    second = await _patch(
        client, headers, {"theme": "light", "dateFormat": "DD.MM.YYYY"}
    )
    read = await client.get(URL, headers=headers)

    assert first.status_code == 200, first.text
    assert first.json()["revision"] == 1
    assert second.json()["revision"] == 2
    assert read.json() == second.json()
    assert read.json()["values"] == {
        "theme": "light",
        "showHints": False,
        "dateFormat": "DD.MM.YYYY",
    }
    assert read.json()["edited_at"] is not None


async def test_null_removes_a_setting(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)
    await _patch(client, headers, {"theme": "dark", "showHints": False})

    response = await _patch(client, headers, {"theme": None})

    assert response.json()["values"] == {"showHints": False}
    assert response.json()["revision"] == 2


async def test_a_patch_that_changes_nothing_keeps_the_revision(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)
    await _patch(client, headers, {"theme": "dark"})

    same = await _patch(client, headers, {"theme": "dark"})
    empty = await _patch(client, headers, {})
    missing = await _patch(client, headers, {"neverSet": None})

    assert [r.json()["revision"] for r in (same, empty, missing)] == [1, 1, 1]
    assert same.json()["values"] == {"theme": "dark"}


async def test_values_keep_their_json_types(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)
    values = {
        "flag": False,
        "count": 3,
        "ratio": 0.5,
        "list": ["a", 1],
        "map": {"k": [True]},
    }

    await _patch(client, headers, values)

    assert (await client.get(URL, headers=headers)).json()["values"] == values


async def test_settings_belong_to_their_account(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    ann = await _account(client, user_engine)
    bob = await _account(client, user_engine, "bob@example.com", "bob")

    await _patch(client, ann, {"theme": "dark"})
    await _patch(client, bob, {"theme": "light"})

    assert (await client.get(URL, headers=ann)).json()["values"] == {"theme": "dark"}
    assert (await client.get(URL, headers=bob)).json()["values"] == {"theme": "light"}


async def test_settings_go_with_the_account(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)
    await _patch(client, headers, {"theme": "dark"})

    async with user_engine.begin() as conn:
        await conn.execute(text('DELETE FROM "user"'))
        counted = await conn.execute(text("SELECT count(*) FROM user_settings"))
        left = counted.scalar_one()

    assert left == 0


async def test_invalid_names_are_rejected(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)

    for name in ("", "1abc", "has space", "a" * 65, "кириллица"):
        response = await _patch(client, headers, {name: 1})
        assert response.status_code == 422, name

    assert (await client.get(URL, headers=headers)).json()["revision"] == 0


async def test_too_many_names_in_one_request_are_rejected(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)

    response = await _patch(client, headers, {f"k{i}": i for i in range(65)})

    assert response.status_code == 422


async def test_the_whole_document_has_a_size_limit(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)
    chunk = "x" * (MAX_SETTINGS_BYTES // 2)
    await _patch(client, headers, {"first": chunk})

    refused = await _patch(client, headers, {"second": chunk})
    after = await client.get(URL, headers=headers)

    assert refused.status_code == 413
    assert refused.json()["detail"] == "SETTINGS_TOO_LARGE"
    assert list(after.json()["values"]) == ["first"]
    assert after.json()["revision"] == 1


async def test_parallel_patches_of_different_names_all_land(
    client: httpx.AsyncClient, user_engine: AsyncEngine
) -> None:
    headers = await _account(client, user_engine)

    responses = await asyncio.gather(
        *(_patch(client, headers, {f"key{i}": i}) for i in range(8))
    )

    assert {r.status_code for r in responses} == {200}
    read = (await client.get(URL, headers=headers)).json()
    assert read["values"] == {f"key{i}": i for i in range(8)}
    assert read["revision"] == 8
