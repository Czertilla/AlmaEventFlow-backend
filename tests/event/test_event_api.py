from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v1"
ADMIN = principal(superuser=True)
USER = principal()


async def _event(
    api: httpx.AsyncClient, name: str = "Concert", **extra: Any
) -> dict[str, Any]:
    response = await api.post(
        f"{BASE}/events", json={"name": name, **extra}, headers=ADMIN
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _collective(engine: AsyncEngine, name: str = "Choir") -> UUID:
    collective_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO organization (id, name, type) "
                "VALUES (:id, :name, 'collective')"
            ),
            {"id": collective_id, "name": name},
        )
        await conn.execute(
            text("INSERT INTO collective (id, is_verified) VALUES (:id, true)"),
            {"id": collective_id},
        )
    return collective_id


async def _person(engine: AsyncEngine, surname: str = "Ivanov") -> UUID:
    person_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO person (id, surname, name) VALUES (:id, :s, 'Ivan')"),
            {"id": person_id, "s": surname},
        )
    return person_id


async def test_event_lifecycle_and_partial_patch(api: httpx.AsyncClient) -> None:
    created = await _event(api, description="Spring", date="2026-05-01")
    event_id = created["id"]

    patched = await api.patch(
        f"{BASE}/events/{event_id}", json={"name": "Concert 2"}, headers=ADMIN
    )
    activated = await api.patch(
        f"{BASE}/events/{event_id}", json={"status": "active"}, headers=ADMIN
    )
    kept = await api.patch(
        f"{BASE}/events/{event_id}", json={"description": "Summer"}, headers=ADMIN
    )
    replaced = await api.put(
        f"{BASE}/events/{event_id}", json={"name": "Gala"}, headers=ADMIN
    )
    read = await api.get(f"{BASE}/events/{event_id}", headers=USER)

    assert created["created_at"]
    assert created["edited_at"] is None
    assert patched.json()["name"] == "Concert 2"
    assert patched.json()["status"] == "draft"
    assert activated.json()["status"] == "active"
    assert kept.json()["status"] == "active"
    assert kept.json()["description"] == "Summer"
    assert replaced.json()["description"] is None
    assert read.json()["edited_at"] is not None


async def test_activating_an_event_announces_it_once_and_edits_refresh_it(
    api: httpx.AsyncClient, notices: list[UUID]
) -> None:
    created = await _event(api, date="2026-05-01")
    event_id = UUID(created["id"])

    activated = await api.patch(
        f"{BASE}/events/{event_id}", json={"status": "active"}, headers=ADMIN
    )
    untouched = await api.patch(
        f"{BASE}/events/{event_id}", json={"description": "Same"}, headers=ADMIN
    )
    renamed = await api.patch(
        f"{BASE}/events/{event_id}", json={"name": "Renamed"}, headers=ADMIN
    )

    assert activated.json()["status"] == "active"
    assert untouched.status_code == 200
    assert renamed.json()["name"] == "Renamed"
    assert notices == [event_id, event_id]


async def test_events_are_filtered_and_sorted(api: httpx.AsyncClient) -> None:
    await _event(api, "Alpha", date="2026-01-01", level="regional", format="online")
    await _event(api, "Beta", date="2026-02-01", level="national", type="concert")
    await _event(api, "Gamma")

    undated = await api.get(
        f"{BASE}/events", params={"date__isnull": True}, headers=USER
    )
    levels = await api.get(
        f"{BASE}/events",
        params={"level__in": "regional,national", "order_by": "-name"},
        headers=USER,
    )
    types = await api.get(
        f"{BASE}/events", params={"type__in": "concert"}, headers=USER
    )
    online = await api.get(f"{BASE}/events", params={"format": "online"}, headers=USER)
    drafts = await api.get(
        f"{BASE}/events",
        params={"status__in": "draft,template", "order_by": "name"},
        headers=USER,
    )
    newest = await api.get(
        f"{BASE}/events", params={"order_by": "-created_at"}, headers=USER
    )
    recent = await api.get(
        f"{BASE}/events",
        params={"created_at__gte": "2020-01-01T00:00:00Z"},
        headers=USER,
    )
    future = await api.get(
        f"{BASE}/events",
        params={"created_at__gte": "2999-01-01T00:00:00Z"},
        headers=USER,
    )
    rejected = await api.get(
        f"{BASE}/events", params={"order_by": "status_id"}, headers=USER
    )

    assert [e["name"] for e in undated.json()["items"]] == ["Gamma"]
    assert [e["name"] for e in levels.json()["items"]] == ["Beta", "Alpha"]
    assert [e["name"] for e in types.json()["items"]] == ["Beta"]
    assert [e["name"] for e in online.json()["items"]] == ["Alpha"]
    assert [e["name"] for e in drafts.json()["items"]] == ["Alpha", "Beta", "Gamma"]
    assert newest.json()["items"][0]["name"] == "Gamma"
    assert recent.json()["pagination"]["total"] == 3
    assert future.json()["pagination"]["total"] == 0
    assert rejected.status_code == 422


async def test_events_sort_by_lookup_rank(api: httpx.AsyncClient) -> None:
    await _event(api, "Alpha", level="regional")
    beta = await _event(api, "Beta", level="international", date="2026-03-01")
    await _event(api, "Gamma", level="internal")
    await _event(api, "Delta")
    activated = await api.patch(
        f"{BASE}/events/{beta['id']}", json={"status": "active"}, headers=ADMIN
    )

    async def names(order_by: str) -> list[str]:
        response = await api.get(
            f"{BASE}/events", params={"order_by": order_by}, headers=USER
        )
        assert response.status_code == 200, response.text
        return [e["name"] for e in response.json()["items"]]

    assert activated.status_code == 200, activated.text
    assert await names("-status,name") == ["Beta", "Alpha", "Delta", "Gamma"]
    assert await names("status,name") == ["Alpha", "Delta", "Gamma", "Beta"]
    assert await names("level") == ["Gamma", "Alpha", "Beta", "Delta"]
    assert await names("-level,name") == ["Delta", "Beta", "Alpha", "Gamma"]


async def test_event_writes_are_for_superusers(api: httpx.AsyncClient) -> None:
    response = await api.post(f"{BASE}/events", json={"name": "Nope"}, headers=USER)

    assert response.status_code == 403


async def test_stages_validate_their_span_and_filter_by_time(
    api: httpx.AsyncClient,
) -> None:
    event = await _event(api)
    stage = await api.post(
        f"{BASE}/stages",
        json={
            "event_id": event["id"],
            "name": "Doors",
            "start_at": "2026-05-01T10:00:00Z",
            "end_at": "2026-05-01T11:00:00Z",
        },
        headers=ADMIN,
    )
    backwards = await api.post(
        f"{BASE}/stages",
        json={
            "event_id": event["id"],
            "name": "Broken",
            "start_at": "2026-05-01T12:00:00Z",
            "end_at": "2026-05-01T11:00:00Z",
        },
        headers=ADMIN,
    )
    patched_back = await api.patch(
        f"{BASE}/stages/{stage.json()['id']}",
        json={"start_at": "2026-05-02T10:00:00Z", "end_at": "2026-05-02T09:00:00Z"},
        headers=ADMIN,
    )
    later = await api.get(
        f"{BASE}/stages",
        params={"start_at__gte": "2026-05-01T09:00:00Z", "order_by": "-start_at"},
        headers=USER,
    )
    later_than = await api.get(
        f"{BASE}/stages",
        params={"start_at__gte": "2026-06-01T00:00:00Z"},
        headers=USER,
    )
    of_event = await api.get(f"{BASE}/events/{event['id']}/stages", headers=USER)

    assert stage.status_code == 200, stage.text
    assert stage.json()["created_at"]
    assert backwards.status_code == 422
    assert patched_back.status_code == 422
    assert [s["name"] for s in later.json()["items"]] == ["Doors"]
    assert later_than.json()["pagination"]["total"] == 0
    assert [s["name"] for s in of_event.json()["items"]] == ["Doors"]


async def test_links_work_end_to_end(api: httpx.AsyncClient) -> None:
    event = await _event(api)
    other = await _event(api, "Other")
    link = await api.post(
        f"{BASE}/links",
        json={
            "event_id": event["id"],
            "url": "https://example.com/tickets",
            "type": "site",
            "description": "Tickets",
        },
        headers=ADMIN,
    )
    assert link.status_code == 200, link.text
    link_id = link.json()["id"]
    await api.post(
        f"{BASE}/links",
        json={"event_id": other["id"], "url": "https://example.com/o", "type": "site"},
        headers=ADMIN,
    )

    read = await api.get(f"{BASE}/links/{link_id}", headers=USER)
    patched = await api.patch(
        f"{BASE}/links/{link_id}", json={"description": "Buy"}, headers=ADMIN
    )
    bad_type = await api.patch(
        f"{BASE}/links/{link_id}", json={"type": "not-a-type"}, headers=ADMIN
    )
    replaced = await api.put(
        f"{BASE}/links/{link_id}",
        json={"url": "https://example.com/new", "type": "site"},
        headers=ADMIN,
    )
    mine = await api.get(
        f"{BASE}/links", params={"event_id": event["id"]}, headers=USER
    )
    found = await api.get(
        f"{BASE}/links", params={"search": "example.com/o"}, headers=USER
    )
    deleted = await api.delete(f"{BASE}/links/{link_id}", headers=ADMIN)

    assert link.status_code == 200, link.text
    assert read.json()["url"] == "https://example.com/tickets"
    assert read.json()["created_at"]
    assert patched.json()["description"] == "Buy"
    assert patched.json()["edited_at"] is not None
    assert bad_type.status_code == 422
    assert (replaced.json()["url"], replaced.json()["description"]) == (
        "https://example.com/new",
        None,
    )
    assert [item["id"] for item in mine.json()["items"]] == [link_id]
    assert found.json()["pagination"]["total"] == 1
    assert deleted.status_code == 200


async def test_roles_members_and_participations(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    collective_id = await _collective(event_engine)
    person_id = await _person(event_engine)
    other_person = await _person(event_engine, "Petrov")
    event = await _event(api)

    role = await api.post(
        f"{BASE}/roles",
        json={"collective_id": str(collective_id), "name": "Singer"},
        headers=ADMIN,
    )
    member = await api.post(
        f"{BASE}/members",
        json={
            "collective_id": str(collective_id),
            "person_id": str(person_id),
            "roles": [role.json()["id"]],
        },
        headers=ADMIN,
    )
    await api.post(
        f"{BASE}/members",
        json={"collective_id": str(collective_id), "person_id": str(other_person)},
        headers=ADMIN,
    )
    participation = await api.post(
        f"{BASE}/participations",
        json={
            "collective_id": str(collective_id),
            "event_id": event["id"],
            "priority_degree": "medium",
        },
        headers=ADMIN,
    )

    found = await api.get(f"{BASE}/members", params={"search": "Petr"}, headers=USER)
    both = await api.get(
        f"{BASE}/members",
        params={"collective_id__in": str(collective_id), "order_by": "-created_at"},
        headers=USER,
    )
    by_surname = await api.get(
        f"{BASE}/members", params={"order_by": "-person__surname"}, headers=USER
    )
    patched_member = await api.patch(
        f"{BASE}/members/{member.json()['id']}",
        json={"is_active": False},
        headers=ADMIN,
    )
    inactive = await api.get(
        f"{BASE}/members", params={"is_active": False}, headers=USER
    )
    roles = await api.get(
        f"{BASE}/roles",
        params={"collective_id__in": str(collective_id), "order_by": "name"},
        headers=USER,
    )
    mid = await api.get(
        f"{BASE}/participations",
        params={"priority_degree__in": "medium,hight", "event_id": event["id"]},
        headers=USER,
    )
    unset = await api.get(
        f"{BASE}/participations",
        params={"priority_degree__isnull": True},
        headers=USER,
    )

    assert role.status_code == 200, role.text
    assert role.json()["created_at"]
    assert member.status_code == 200, member.text
    assert member.json()["created_at"]
    assert [r["name"] for r in member.json()["roles"]] == ["Singer"]
    assert participation.status_code == 200, participation.text
    assert participation.json()["created_at"]
    assert [m["person_id"] for m in found.json()["items"]] == [str(other_person)]
    assert both.json()["pagination"]["total"] == 2
    assert [m["person_id"] for m in by_surname.json()["items"]] == [
        str(other_person),
        str(person_id),
    ]
    assert patched_member.json()["is_active"] is False
    assert patched_member.json()["edited_at"] is not None
    assert [m["id"] for m in inactive.json()["items"]] == [member.json()["id"]]
    assert [r["name"] for r in roles.json()["items"]] == ["Singer"]
    assert [p["id"] for p in mid.json()["items"]] == [participation.json()["id"]]
    assert unset.json()["pagination"]["total"] == 0


async def test_rewards_are_multipart_forms_and_files_are_optional(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    collective_id = await _collective(event_engine)
    event = await _event(api)
    participation = await api.post(
        f"{BASE}/participations",
        json={"collective_id": str(collective_id), "event_id": event["id"]},
        headers=ADMIN,
    )
    participation_id = participation.json()["id"]

    created = await api.post(
        f"{BASE}/rewards",
        data={"participation_id": participation_id, "name": "Gold", "degree": "1"},
        headers=ADMIN,
    )
    reward_id = created.json()["id"]
    patched = await api.patch(
        f"{BASE}/rewards/{reward_id}", data={"name": "Platinum"}, headers=ADMIN
    )
    replaced = await api.put(
        f"{BASE}/rewards/{reward_id}",
        json={"name": "Silver", "degree": 2},
        headers=ADMIN,
    )
    filtered = await api.get(
        f"{BASE}/rewards",
        params={"participation_id": participation_id, "degree__in": "2,3"},
        headers=USER,
    )
    ordered = await api.get(
        f"{BASE}/rewards", params={"order_by": "-degree"}, headers=USER
    )

    assert created.status_code == 200, created.text
    assert created.json()["created_at"]
    assert created.json()["file_link"] is None
    assert patched.status_code == 200, patched.text
    assert (patched.json()["name"], patched.json()["degree"]) == ("Platinum", 1)
    assert patched.json()["edited_at"] is not None
    assert replaced.json()["name"] == "Silver"
    assert [r["id"] for r in filtered.json()["items"]] == [reward_id]
    assert ordered.status_code == 200


async def test_attendance_filters(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    collective_id = await _collective(event_engine)
    person_id = await _person(event_engine)
    event = await _event(api)
    participation = await api.post(
        f"{BASE}/participations",
        json={"collective_id": str(collective_id), "event_id": event["id"]},
        headers=ADMIN,
    )
    member = await api.post(
        f"{BASE}/members",
        json={"collective_id": str(collective_id), "person_id": str(person_id)},
        headers=ADMIN,
    )
    created = await api.post(
        f"{BASE}/attendances",
        json={
            "member_id": member.json()["id"],
            "participation_id": participation.json()["id"],
            "is_attended": True,
        },
        headers=ADMIN,
    )

    attended = await api.get(
        f"{BASE}/attendances", params={"is_attended": True}, headers=USER
    )
    absent = await api.get(
        f"{BASE}/attendances", params={"is_attended": False}, headers=USER
    )
    verified = await api.get(
        f"{BASE}/attendances", params={"is_verified": False}, headers=USER
    )
    of_member = await api.get(
        f"{BASE}/attendances",
        params={"member_id__in": member.json()["id"], "order_by": "-created_at"},
        headers=USER,
    )
    edited = await api.get(
        f"{BASE}/attendances", params={"edited_at__isnull": False}, headers=USER
    )

    assert created.status_code == 200, created.text
    assert created.json()["created_at"]
    assert attended.json()["pagination"]["total"] == 1
    assert absent.json()["pagination"]["total"] == 0
    assert verified.json()["pagination"]["total"] == 1
    assert of_member.json()["pagination"]["total"] == 1
    assert edited.json()["pagination"]["total"] == 0
