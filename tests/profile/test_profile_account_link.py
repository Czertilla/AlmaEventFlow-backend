from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from support.http import principal

from core.enum.profile import PersonLinkSource
from core.schema.message.profile import LinkAccountRequest

Maker = async_sessionmaker[AsyncSession]
ADMIN_ID = uuid4()
ADMIN = principal(superuser=True, user_id=ADMIN_ID)


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


async def _history(
    engine: AsyncEngine,
) -> list[tuple[UUID, UUID | None, UUID | None, str, str, UUID | None]]:
    async with engine.connect() as conn:
        rows = await conn.execute(
            text(
                "SELECT user_id, old_person_id, new_person_id, action, source, "
                "actor_id FROM person_account_history ORDER BY created_at"
            )
        )
        return [
            (
                row.user_id,
                row.old_person_id,
                row.new_person_id,
                row.action,
                row.source,
                row.actor_id,
            )
            for row in rows
        ]


async def _ask(
    maker: Maker,
    user_id: UUID,
    person_id: UUID,
    *,
    replace: bool = False,
    source: PersonLinkSource = PersonLinkSource.INVITE,
    actor_id: UUID | None = None,
) -> Any:
    from profile.api.kafka.sub.account import on_link_account
    from profile.uow.person import PersonUOW

    return await on_link_account(
        LinkAccountRequest(
            user_id=user_id,
            person_id=person_id,
            replace=replace,
            source=source,
            actor_id=actor_id,
        ),
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


async def test_a_link_leaves_a_history_row_with_its_author_and_reason(
    api: httpx.AsyncClient, profile_sessionmaker: Maker, profile_engine: AsyncEngine
) -> None:
    person_id, user_id = await _person(api), uuid4()

    await _ask(profile_sessionmaker, user_id, person_id, actor_id=user_id)
    await _ask(profile_sessionmaker, user_id, person_id, actor_id=user_id)

    assert await _history(profile_engine) == [
        (user_id, None, person_id, "linked", "invite", user_id)
    ]


async def test_moving_an_account_is_one_replaced_row_made_by_the_admin(
    api: httpx.AsyncClient, profile_sessionmaker: Maker, profile_engine: AsyncEngine
) -> None:
    first, second = await _person(api), await _person(api, "Petrov")
    user_id = uuid4()
    await _ask(profile_sessionmaker, user_id, first, actor_id=user_id)

    await _ask(
        profile_sessionmaker,
        user_id,
        second,
        replace=True,
        source=PersonLinkSource.ADMIN,
        actor_id=ADMIN_ID,
    )

    assert await _history(profile_engine) == [
        (user_id, None, first, "linked", "invite", user_id),
        (user_id, first, second, "replaced", "admin", ADMIN_ID),
    ]


async def test_a_refused_link_leaves_no_history(
    api: httpx.AsyncClient, profile_sessionmaker: Maker, profile_engine: AsyncEngine
) -> None:
    first, second = await _person(api), await _person(api, "Petrov")
    owner, newcomer = uuid4(), uuid4()
    await _ask(profile_sessionmaker, owner, first)

    await _ask(profile_sessionmaker, newcomer, first)
    await _ask(profile_sessionmaker, owner, second)
    await _ask(profile_sessionmaker, newcomer, uuid4())

    assert [row[0] for row in await _history(profile_engine)] == [owner]


async def test_deleting_a_person_writes_who_unlinked_the_account_and_keeps_the_trace(
    api: httpx.AsyncClient, profile_sessionmaker: Maker, profile_engine: AsyncEngine
) -> None:
    person_id, user_id = await _person(api), uuid4()
    await _ask(profile_sessionmaker, user_id, person_id, actor_id=user_id)

    deleted = await api.delete(f"/profile/v1/persons/{person_id}", headers=ADMIN)

    assert deleted.status_code == 200
    assert await _history(profile_engine) == [
        (user_id, None, person_id, "linked", "invite", user_id),
        (user_id, person_id, None, "unlinked", "person_deleted", ADMIN_ID),
    ]


async def test_deleting_a_person_nobody_is_linked_to_writes_nothing(
    api: httpx.AsyncClient, profile_engine: AsyncEngine
) -> None:
    person_id = await _person(api)

    await api.delete(f"/profile/v1/persons/{person_id}", headers=ADMIN)

    assert await _history(profile_engine) == []


def test_the_action_follows_from_the_two_ends_of_the_change() -> None:
    from profile.enum.account import PersonLinkAction

    one, other = uuid4(), uuid4()

    assert PersonLinkAction.of(None, one) == "linked"
    assert PersonLinkAction.of(one, other) == "replaced"
    assert PersonLinkAction.of(one, None) == "unlinked"


HISTORY = "/profile/v2/account-links/history"


async def test_the_history_lists_the_changes_newest_first_with_all_their_facts(
    api: httpx.AsyncClient, profile_sessionmaker: Maker
) -> None:
    person_id, user_id = await _person(api), uuid4()
    other = await _person(api, "Petrov")
    await _ask(profile_sessionmaker, user_id, person_id, actor_id=user_id)
    await _ask(
        profile_sessionmaker,
        user_id,
        other,
        replace=True,
        source=PersonLinkSource.ADMIN,
        actor_id=ADMIN_ID,
    )

    response = await api.get(HISTORY, headers=ADMIN)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["pagination"]["total"] == 2
    assert [
        (
            item["user_id"],
            item["old_person_id"],
            item["new_person_id"],
            item["action"],
            item["source"],
            item["actor_id"],
        )
        for item in body["items"]
    ] == [
        (str(user_id), str(person_id), str(other), "replaced", "admin", str(ADMIN_ID)),
        (str(user_id), None, str(person_id), "linked", "invite", str(user_id)),
    ]
    assert body["items"][0]["created_at"] >= body["items"][1]["created_at"]


async def test_the_history_can_be_narrowed_and_ordered(
    api: httpx.AsyncClient, profile_sessionmaker: Maker
) -> None:
    first, second, third = [await _person(api, name) for name in ("A", "B", "C")]
    ann, bob, cid = uuid4(), uuid4(), uuid4()
    await _ask(profile_sessionmaker, ann, first, actor_id=ann)
    await _ask(profile_sessionmaker, bob, second, actor_id=bob)
    await _ask(
        profile_sessionmaker,
        cid,
        third,
        source=PersonLinkSource.ADMIN,
        actor_id=ADMIN_ID,
    )

    async def users(**params: str) -> list[str]:
        response = await api.get(HISTORY, params=params, headers=ADMIN)
        assert response.status_code == 200, response.text
        return [item["user_id"] for item in response.json()["items"]]

    listed = (await api.get(HISTORY, headers=ADMIN)).json()["items"]
    bobs_moment = next(i["created_at"] for i in listed if i["user_id"] == str(bob))
    assert await users(user_id=str(ann)) == [str(ann)]
    assert await users(person_id=str(second)) == [str(bob)]
    assert await users(actor_id=str(ADMIN_ID)) == [str(cid)]
    assert await users(source="admin") == [str(cid)]
    assert await users(source="invite", order_by="created_at") == [str(ann), str(bob)]
    assert await users(action="linked", order_by="-created_at") == [
        str(cid),
        str(bob),
        str(ann),
    ]
    assert await users(action="unlinked") == []
    assert await users(created_at__gte=bobs_moment) == [str(cid), str(bob)]
    assert await users(created_at__lte=bobs_moment, order_by="created_at") == [
        str(ann),
        str(bob),
    ]
    assert await users(created_at__gte="2999-01-01T00:00:00Z") == []


async def test_a_person_filter_finds_a_change_on_either_end(
    api: httpx.AsyncClient, profile_sessionmaker: Maker
) -> None:
    first, second = await _person(api), await _person(api, "Petrov")
    user_id = uuid4()
    await _ask(profile_sessionmaker, user_id, first, actor_id=user_id)
    await _ask(
        profile_sessionmaker,
        user_id,
        second,
        replace=True,
        source=PersonLinkSource.ADMIN,
        actor_id=ADMIN_ID,
    )

    async def actions(person_id: UUID) -> list[str]:
        response = await api.get(
            HISTORY, params={"person_id": str(person_id)}, headers=ADMIN
        )
        return [item["action"] for item in response.json()["items"]]

    assert await actions(first) == ["replaced", "linked"]
    assert await actions(second) == ["replaced"]


async def test_the_history_is_paged_and_only_for_superusers(
    api: httpx.AsyncClient, profile_sessionmaker: Maker
) -> None:
    person_id, user_id = await _person(api), uuid4()
    await _ask(profile_sessionmaker, user_id, person_id)

    page = await api.get(HISTORY, params={"limit": 1, "page": 2}, headers=ADMIN)
    ordinary = await api.get(HISTORY, headers=principal())
    anonymous = await api.get(HISTORY)

    assert page.status_code == 200
    assert page.json()["items"] == []
    assert page.json()["pagination"]["total"] == 1
    assert ordinary.status_code == 403
    assert anonymous.status_code == 401


@pytest.mark.parametrize(
    "params", [{"order_by": "user_id"}, {"action": "kidnapped"}, {"source": "magic"}]
)
async def test_the_history_refuses_what_it_cannot_filter_by(
    api: httpx.AsyncClient, params: dict[str, str]
) -> None:
    response = await api.get(HISTORY, params=params, headers=ADMIN)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE person_account_history SET source = 'admin'",
        "DELETE FROM person_account_history",
    ],
)
async def test_the_history_cannot_be_rewritten_even_by_sql(
    api: httpx.AsyncClient,
    profile_sessionmaker: Maker,
    profile_engine: AsyncEngine,
    statement: str,
) -> None:
    person_id, user_id = await _person(api), uuid4()
    await _ask(profile_sessionmaker, user_id, person_id, actor_id=user_id)

    with pytest.raises(DBAPIError, match="append-only"):
        async with profile_engine.begin() as conn:
            await conn.execute(text(statement))

    assert len(await _history(profile_engine)) == 1
