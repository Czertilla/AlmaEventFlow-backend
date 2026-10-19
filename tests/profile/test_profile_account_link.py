from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from support.http import principal

from core.schema.message.profile import LinkAccountRequest

Maker = async_sessionmaker[AsyncSession]
ADMIN = principal(superuser=True)


async def _person(api: httpx.AsyncClient, surname: str = "Ivanov") -> UUID:
    response = await api.post(
        "/profile/v1/persons", json={"surname": surname, "name": "I"}, headers=ADMIN
    )
    return UUID(response.json()["id"])


async def _links(engine: AsyncEngine) -> list[tuple[UUID, UUID]]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text("SELECT person_id, user_id FROM person_account ORDER BY created_at")
        )
        return [(row.person_id, row.user_id) for row in rows]


async def _ask(
    maker: Maker, user_id: UUID, person_id: UUID, *, replace: bool = False
) -> Any:
    from profile.api.kafka.sub.account import on_link_account
    from profile.uow.person import PersonUOW

    return await on_link_account(
        LinkAccountRequest(user_id=user_id, person_id=person_id, replace=replace),
        PersonUOW(maker),
    )


async def test_the_link_rpc_links_an_account_and_announces_the_state(
    api: httpx.AsyncClient,
    profile_sessionmaker: Maker,
    profile_engine: AsyncEngine,
    published: list[tuple[str, Any]],
) -> None:
    person_id, user_id = await _person(api), uuid4()

    answer = await _ask(profile_sessionmaker, user_id, person_id)
    again = await _ask(profile_sessionmaker, user_id, person_id)

    assert answer.error is None and again.error is None
    assert await _links(profile_engine) == [(person_id, user_id)]
    states = [
        payload[0] for name, payload in published if name == "on_person_link_changed"
    ]
    assert [(s.user_id, s.person_id) for s in states] == [
        (user_id, person_id),
        (user_id, person_id),
    ]


async def test_a_link_is_refused_when_either_side_is_taken(
    api: httpx.AsyncClient, profile_sessionmaker: Maker, profile_engine: AsyncEngine
) -> None:
    first, second = await _person(api), await _person(api, "Petrov")
    owner, newcomer = uuid4(), uuid4()
    await _ask(profile_sessionmaker, owner, first)

    taken = await _ask(profile_sessionmaker, newcomer, first)
    already = await _ask(profile_sessionmaker, owner, second)
    missing = await _ask(profile_sessionmaker, newcomer, uuid4())

    assert (taken.error.code, taken.error.detail) == (400, "PERSON_ALREADY_HAS_ACCOUNT")
    assert (already.error.code, already.error.detail) == (400, "ACCOUNT_ALREADY_LINKED")
    assert (missing.error.code, missing.error.detail) == (404, "PERSON_NOT_FOUND")
    assert await _links(profile_engine) == [(first, owner)]


async def test_an_account_can_be_moved_to_another_person_on_request(
    api: httpx.AsyncClient, profile_sessionmaker: Maker, profile_engine: AsyncEngine
) -> None:
    first, second = await _person(api), await _person(api, "Petrov")
    user_id = uuid4()
    await _ask(profile_sessionmaker, user_id, first)

    moved = await _ask(profile_sessionmaker, user_id, second, replace=True)

    assert moved.error is None
    assert await _links(profile_engine) == [(second, user_id)]


async def test_deleting_a_person_announces_that_the_account_has_none(
    api: httpx.AsyncClient,
    profile_sessionmaker: Maker,
    profile_engine: AsyncEngine,
    published: list[tuple[str, Any]],
) -> None:
    person_id, user_id = await _person(api), uuid4()
    await _ask(profile_sessionmaker, user_id, person_id)
    published.clear()

    deleted = await api.delete(f"/profile/v1/persons/{person_id}", headers=ADMIN)

    assert deleted.status_code == 200
    assert await _links(profile_engine) == []
    assert [name for name, _ in published] == [
        "on_person_link_changed",
        "on_person_deleted",
    ]
    state = published[0][1][0]
    assert (state.user_id, state.person_id) == (user_id, None)
