from datetime import UTC, datetime, timedelta
from profile.registry import FIELDS
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
import pytest
from sqlalchemy import event as sa_event
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine
from support.event import FakeEvent
from support.http import AsPerson, principal

from core.config.settings import settings

V1 = "/profile/v1"
V2 = "/profile/v2"
ADMIN_ID = uuid4()
ADMIN = principal(superuser=True, user_id=ADMIN_ID)
FULLNAME = "person.fullname"


async def _person(api: httpx.AsyncClient, surname: str = "Ivanov") -> UUID:
    response = await api.post(
        f"{V1}/persons", json={"surname": surname, "name": "Ivan"}, headers=ADMIN
    )
    assert response.status_code == 200, response.text
    return UUID(response.json()["id"])


async def _sql(
    engine: AsyncEngine, query: str, **params: object
) -> list[tuple[object, ...]]:
    async with engine.begin() as conn:
        result = await conn.execute(text(query), params)
        return [tuple(row) for row in result.all()] if result.returns_rows else []


async def _recent_link(
    engine: AsyncEngine, person_id: UUID, *, hours_ago: float = 1.0
) -> None:
    await _sql(
        engine,
        "INSERT INTO person_account_history (id, user_id, old_person_id, "
        "new_person_id, action, source, actor_id, created_at) VALUES "
        "(gen_random_uuid(), :user, NULL, :person, 'linked', 'invite', NULL, :at)",
        user=uuid5(NAMESPACE_URL, str(person_id)),
        person=person_id,
        at=datetime.now(UTC) - timedelta(hours=hours_ago),
    )


async def _unit(engine: AsyncEngine, kind: str, head_id: UUID) -> None:
    await _sql(
        engine,
        "INSERT INTO organization (id, type, principal_id) VALUES (:id, :type, :head)",
        id=uuid4(),
        type=kind,
        head=head_id,
    )


async def _rows(engine: AsyncEngine, person_id: UUID) -> list[tuple[object, ...]]:
    return await _sql(
        engine,
        "SELECT field_key, audience FROM person_field_visibility "
        "WHERE person_id = :p ORDER BY field_key",
        p=person_id,
    )


async def _history(engine: AsyncEngine, person_id: UUID) -> list[tuple[object, ...]]:
    return await _sql(
        engine,
        "SELECT field_key, old_audience, new_audience, source, actor_user_id "
        "FROM person_field_visibility_history WHERE person_id = :p "
        "ORDER BY created_at, id",
        p=person_id,
    )


async def _outbox(engine: AsyncEngine, person_id: UUID) -> list[tuple[object, ...]]:
    return await _sql(
        engine,
        "SELECT category, title, body, data, status FROM notification_outbox "
        "WHERE person_id = :p ORDER BY created_at",
        p=person_id,
    )


def _entries(response: httpx.Response) -> dict[str, dict[str, object]]:
    assert response.status_code == 200, response.text
    return {item["key"]: item for item in response.json()["items"]}


async def test_the_settings_page_lists_every_field_with_its_defaults(
    api: httpx.AsyncClient, as_person: AsPerson
) -> None:
    me = await as_person(await _person(api))

    entries = _entries(await api.get(f"{V2}/visibility/my", headers=me))

    assert set(entries) == {field.key for field in FIELDS}
    fullname = entries[FULLNAME]
    assert fullname["label"] == "ФИО"
    assert (fullname["audience_min"], fullname["audience_max"]) == (
        "context",
        "all_users",
    )
    assert (fullname["audience"], fullname["is_default"]) == ("context", True)
    assert fullname["configurable"] is True
    passport = entries["passport.number"]
    assert passport["configurable"] is False
    assert passport["audience"] == "private"


async def test_the_settings_page_of_a_caller_without_a_person_shows_defaults(
    api: httpx.AsyncClient,
) -> None:
    entries = _entries(
        await api.get(
            f"{V2}/visibility/my", headers=principal(person_id=None, user_id=uuid4())
        )
    )

    assert entries[FULLNAME]["audience"] == "context"


async def test_the_head_of_a_unit_sees_the_wider_default(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    head_id = await _person(api, "Dean")
    await _unit(profile_engine, "faculty", head_id)

    entries = _entries(
        await api.get(f"{V2}/visibility/my", headers=await as_person(head_id))
    )

    assert entries[FULLNAME]["audience_default"] == "all_users"
    assert entries[FULLNAME]["audience"] == "all_users"
    assert entries[FULLNAME]["is_default"] is True


async def test_the_settings_need_a_verified_user_with_a_person(
    api: httpx.AsyncClient, as_person: AsPerson
) -> None:
    body = {"audience": "all_users"}
    url = f"{V2}/visibility/my/{FULLNAME}"

    anonymous = await api.put(url, json=body)
    unverified = await api.put(
        url, json=body, headers=principal(person_id=uuid4(), verified=False)
    )
    nobody = await api.put(
        url, json=body, headers=principal(person_id=None, user_id=uuid4())
    )
    listed = await api.get(f"{V2}/visibility/my")

    assert anonymous.status_code == listed.status_code == 401
    assert unverified.status_code == 403
    assert nobody.status_code == 400
    assert nobody.json()["detail"] == "ATTACHED_PERSON_REQUIRED"


async def test_an_owner_opens_the_full_name_and_others_see_it(
    api: httpx.AsyncClient, as_person: AsPerson, event: FakeEvent
) -> None:
    owner_id = await _person(api, "Owner")
    stranger = await as_person(await _person(api, "Stranger"))
    me = await as_person(owner_id)
    before = await api.get(f"{V1}/persons/{owner_id}", headers=stranger)
    event.calls.clear()

    put = await api.put(
        f"{V2}/visibility/my/{FULLNAME}", json={"audience": "all_users"}, headers=me
    )
    after = await api.get(f"{V1}/persons/{owner_id}", headers=stranger)
    names = await api.post(
        f"{V2}/persons/names", json={"ids": [str(owner_id)]}, headers=stranger
    )

    assert before.status_code == 404
    assert put.status_code == 200, put.text
    assert (put.json()["audience"], put.json()["is_default"]) == ("all_users", False)
    assert after.status_code == 200
    assert names.json()["items"][0]["surname"] == "Owner"
    assert event.calls == []


async def test_returning_to_the_default_removes_the_row_and_hides_the_name_again(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    owner_id = await _person(api, "Owner")
    stranger = await as_person(await _person(api, "Stranger"))
    me = await as_person(owner_id)
    await api.put(
        f"{V2}/visibility/my/{FULLNAME}", json={"audience": "all_users"}, headers=me
    )
    assert await _rows(profile_engine, owner_id) == [(FULLNAME, "all_users")]

    reset = await api.delete(f"{V2}/visibility/my/{FULLNAME}", headers=me)
    narrowed = await api.put(
        f"{V2}/visibility/my/{FULLNAME}", json={"audience": "context"}, headers=me
    )
    seen = await api.get(f"{V1}/persons/{owner_id}", headers=stranger)

    assert reset.status_code == narrowed.status_code == 200
    assert (reset.json()["audience"], reset.json()["is_default"]) == ("context", True)
    assert await _rows(profile_engine, owner_id) == []
    assert seen.status_code == 404


async def test_a_head_narrows_the_full_name_to_the_context(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    head_id = await _person(api, "Dean")
    await _unit(profile_engine, "faculty", head_id)
    stranger = await as_person(await _person(api, "Stranger"))
    open_before = await api.get(f"{V1}/persons/{head_id}", headers=stranger)

    put = await api.put(
        f"{V2}/visibility/my/{FULLNAME}",
        json={"audience": "context"},
        headers=await as_person(head_id),
    )
    hidden = await api.get(f"{V1}/persons/{head_id}", headers=stranger)

    assert open_before.status_code == 200
    assert (put.status_code, put.json()["is_default"]) == (200, False)
    assert await _rows(profile_engine, head_id) == [(FULLNAME, "context")]
    assert hidden.status_code == 404


async def test_a_setting_outside_the_range_of_the_field_is_refused(
    api: httpx.AsyncClient, as_person: AsPerson
) -> None:
    me = await as_person(await _person(api))

    below = await api.put(
        f"{V2}/visibility/my/{FULLNAME}", json={"audience": "private"}, headers=me
    )
    above = await api.put(
        f"{V2}/visibility/my/profile.diet", json={"audience": "all_users"}, headers=me
    )
    fixed = await api.put(
        f"{V2}/visibility/my/passport.number",
        json={"audience": "all_users"},
        headers=me,
    )
    reset_fixed = await api.delete(f"{V2}/visibility/my/passport.number", headers=me)
    unknown = await api.put(
        f"{V2}/visibility/my/person.nickname", json={"audience": "context"}, headers=me
    )
    nonsense = await api.put(
        f"{V2}/visibility/my/{FULLNAME}", json={"audience": "everybody"}, headers=me
    )

    assert below.status_code == above.status_code == 422
    assert below.json()["detail"] == above.json()["detail"] == "VISIBILITY_OUT_OF_RANGE"
    assert fixed.status_code == reset_fixed.status_code == 422
    assert fixed.json()["detail"] == "VISIBILITY_NOT_CONFIGURABLE"
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "VISIBILITY_FIELD_NOT_FOUND"
    assert nonsense.status_code == 422


async def test_a_change_touches_only_the_callers_own_row(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    mine, theirs = await _person(api, "Mine"), await _person(api, "Theirs")

    await api.put(
        f"{V2}/visibility/my/{FULLNAME}",
        json={"audience": "all_users"},
        headers=await as_person(mine),
    )

    assert await _rows(profile_engine, mine) == [(FULLNAME, "all_users")]
    assert await _rows(profile_engine, theirs) == []


async def test_every_change_is_kept_in_the_history_with_who_made_it(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    owner_id = await _person(api)
    user_id = uuid5(NAMESPACE_URL, str(owner_id))
    me = await as_person(owner_id)
    url = f"{V2}/visibility/my/{FULLNAME}"

    await api.put(url, json={"audience": "all_users"}, headers=me)
    await api.put(url, json={"audience": "all_users"}, headers=me)
    await api.put(url, json={"audience": "context"}, headers=me)

    assert await _history(profile_engine, owner_id) == [
        (FULLNAME, None, "all_users", "owner", user_id),
        (FULLNAME, "all_users", None, "owner", user_id),
    ]


async def test_the_history_cannot_be_rewritten(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    owner_id = await _person(api)
    await api.put(
        f"{V2}/visibility/my/{FULLNAME}",
        json={"audience": "all_users"},
        headers=await as_person(owner_id),
    )

    for statement in (
        "UPDATE person_field_visibility_history SET new_audience = 'private'",
        "DELETE FROM person_field_visibility_history",
        "TRUNCATE person_field_visibility_history",
    ):
        with pytest.raises(DBAPIError, match="append-only"):
            await _sql(profile_engine, statement)

    assert len(await _history(profile_engine, owner_id)) == 1


async def test_widening_is_held_back_after_the_link_changed_but_narrowing_is_not(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    owner_id = await _person(api, "Owner")
    me = await as_person(owner_id)
    await _recent_link(profile_engine, owner_id, hours_ago=1)

    widening = await api.put(
        f"{V2}/visibility/my/{FULLNAME}", json={"audience": "all_users"}, headers=me
    )
    other_widening = await api.put(
        f"{V2}/visibility/my/profile.birthdate",
        json={"audience": "context"},
        headers=me,
    )

    assert widening.status_code == other_widening.status_code == 409
    assert widening.json()["detail"] == "VISIBILITY_COOLDOWN"
    assert int(widening.headers["retry-after"]) > 0
    assert await _rows(profile_engine, owner_id) == []


async def test_narrowing_is_allowed_during_the_pause(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    head_id = await _person(api, "Dean")
    await _unit(profile_engine, "faculty", head_id)
    await _recent_link(profile_engine, head_id, hours_ago=1)

    response = await api.put(
        f"{V2}/visibility/my/{FULLNAME}",
        json={"audience": "context"},
        headers=await as_person(head_id),
    )

    assert response.status_code == 200, response.text


async def test_widening_is_allowed_once_the_pause_is_over(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    owner_id = await _person(api)
    await _recent_link(
        profile_engine, owner_id, hours_ago=settings.LINK_COOLDOWN_HOURS + 1
    )

    response = await api.put(
        f"{V2}/visibility/my/{FULLNAME}",
        json={"audience": "all_users"},
        headers=await as_person(owner_id),
    )

    assert response.status_code == 200, response.text


async def test_the_pause_can_be_switched_off(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    as_person: AsPerson,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id = await _person(api)
    await _recent_link(profile_engine, owner_id, hours_ago=0.1)
    monkeypatch.setattr(settings, "LINK_COOLDOWN_HOURS", 0)

    response = await api.put(
        f"{V2}/visibility/my/{FULLNAME}",
        json={"audience": "all_users"},
        headers=await as_person(owner_id),
    )

    assert response.status_code == 200, response.text


async def test_widening_tells_the_owner_and_narrowing_does_not(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    owner_id = await _person(api, "Owner")
    me = await as_person(owner_id)

    await api.put(
        f"{V2}/visibility/my/{FULLNAME}", json={"audience": "all_users"}, headers=me
    )
    await api.put(
        f"{V2}/visibility/my/{FULLNAME}", json={"audience": "all_users"}, headers=me
    )
    await api.put(
        f"{V2}/visibility/my/{FULLNAME}", json={"audience": "context"}, headers=me
    )

    notices = await _outbox(profile_engine, owner_id)
    assert len(notices) == 1
    category, title, body, data, status = notices[0]
    assert (category, status) == ("system", "pending")
    assert title == "Видимость данных расширена"
    assert isinstance(body, str)
    assert "«ФИО»" in body
    assert "всем пользователям" in body
    assert "Owner" not in body
    assert data == {
        "kind": "visibility_widened",
        "field": FULLNAME,
        "audience": "all_users",
    }


async def test_a_failed_notification_rolls_the_setting_back(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    as_person: AsPerson,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id = await _person(api)
    me = await as_person(owner_id)

    async def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError("outbox is down")

    monkeypatch.setattr(
        "profile.repository.outbox.NotificationOutboxRepo.enqueue", broken
    )

    with pytest.raises(RuntimeError):
        await api.put(
            f"{V2}/visibility/my/{FULLNAME}", json={"audience": "all_users"}, headers=me
        )

    assert await _rows(profile_engine, owner_id) == []
    assert await _history(profile_engine, owner_id) == []


async def test_an_administrator_sets_and_resets_a_field_for_a_person(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    owner_id = await _person(api)
    await _recent_link(profile_engine, owner_id, hours_ago=1)
    url = f"{V2}/persons/{owner_id}/visibility"

    put = await api.put(
        f"{url}/{FULLNAME}", json={"audience": "all_users"}, headers=ADMIN
    )
    listed = _entries(await api.get(url, headers=ADMIN))
    reset = await api.delete(f"{url}/{FULLNAME}", headers=ADMIN)
    forbidden = await api.put(
        f"{url}/{FULLNAME}",
        json={"audience": "all_users"},
        headers=await as_person(owner_id),
    )
    missing = await api.put(
        f"{V2}/persons/{uuid4()}/visibility/{FULLNAME}",
        json={"audience": "all_users"},
        headers=ADMIN,
    )

    assert put.status_code == reset.status_code == 200, put.text
    assert listed[FULLNAME]["audience"] == "all_users"
    assert forbidden.status_code == 403
    assert missing.status_code == 404
    assert missing.json()["detail"] == "PERSON_NOT_FOUND"
    assert [row[1:4] for row in await _history(profile_engine, owner_id)] == [
        (None, "all_users", "admin"),
        ("all_users", None, "admin"),
    ]
    assert await _rows(profile_engine, owner_id) == []


async def test_a_stored_audience_is_kept_within_the_range_after_the_registry_narrows(
    api: httpx.AsyncClient, profile_engine: AsyncEngine, as_person: AsPerson
) -> None:
    owner_id = await _person(api)
    await _sql(
        profile_engine,
        "INSERT INTO person_field_visibility "
        "(person_id, field_key, audience, created_at) "
        "VALUES (:p, 'profile.diet', 'all_users', now())",
        p=owner_id,
    )

    entries = _entries(
        await api.get(f"{V2}/visibility/my", headers=await as_person(owner_id))
    )

    assert entries["profile.diet"]["audience"] == "context"
    assert entries["profile.diet"]["is_default"] is False


async def test_many_subjects_cost_the_same_number_of_queries_and_event_calls(
    api: httpx.AsyncClient,
    profile_engine: AsyncEngine,
    as_person: AsPerson,
    event: FakeEvent,
) -> None:
    viewer_id = await _person(api, "Viewer")
    viewer = await as_person(viewer_id)
    crowd = [await _person(api, f"Crowd{i}") for i in range(40)]
    for person_id in crowd[:20]:
        event.share(viewer_id, person_id)
    statements: list[str] = []

    def count(conn: object, cursor: object, statement: str, *rest: object) -> None:
        statements.append(statement)

    async def ask(ids: list[UUID]) -> tuple[int, int]:
        statements.clear()
        event.calls.clear()
        response = await api.post(
            f"{V2}/persons/names", json={"ids": [str(i) for i in ids]}, headers=viewer
        )
        assert response.status_code == 200, response.text
        assert len(response.json()["items"]) == len(ids)
        return len(statements), len(event.calls)

    sa_event.listen(profile_engine.sync_engine, "before_cursor_execute", count)
    try:
        few = await ask(crowd[:5])
        many = await ask(crowd)
    finally:
        sa_event.remove(profile_engine.sync_engine, "before_cursor_execute", count)

    assert few == many
    assert many[1] == 1
