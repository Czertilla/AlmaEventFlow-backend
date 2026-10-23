import datetime
from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v2/collectives"
TODAY = datetime.date.today()


def _day(offset: int) -> datetime.date:
    return TODAY + datetime.timedelta(days=offset)


@dataclass
class Seed:
    leader: UUID
    collective: UUID
    members: list[UUID]
    persons: list[UUID]


async def _person(engine: AsyncEngine, surname: str) -> UUID:
    person_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO person (id, surname, name) VALUES (:id, :s, 'Ivan')"),
            {"id": person_id, "s": surname},
        )
    return person_id


async def _collective(engine: AsyncEngine, name: str, leader: UUID) -> UUID:
    collective_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO organization (id, name, type, principal_id) "
                "VALUES (:id, :name, 'collective', :leader)"
            ),
            {"id": collective_id, "name": name, "leader": leader},
        )
        await conn.execute(
            text("INSERT INTO collective (id, is_verified) VALUES (:id, true)"),
            {"id": collective_id},
        )
    return collective_id


async def _member(
    engine: AsyncEngine, person: UUID, collective: UUID, *, active: bool = True
) -> UUID:
    member_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO member (id, person_id, collective_id, is_active, "
                "created_at) VALUES (:id, :person, :collective, :active, now())"
            ),
            {
                "id": member_id,
                "person": person,
                "collective": collective,
                "active": active,
            },
        )
    return member_id


async def _event(
    engine: AsyncEngine,
    collective: UUID,
    name: str,
    offset: int | None,
    *,
    status: str = "active",
    type: str | None = None,
) -> UUID:
    event_id, participation_id = uuid4(), uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO event (id, name, date, status_id, type_id, created_at) "
                "VALUES (:id, :name, :date, "
                "(SELECT id FROM event_status WHERE name = :status), "
                "(SELECT id FROM event_type WHERE name = :type), now())"
            ),
            {
                "id": event_id,
                "name": name,
                "date": _day(offset) if offset is not None else None,
                "status": status,
                "type": type,
            },
        )
        await conn.execute(
            text(
                "INSERT INTO participation (id, collective_id, event_id, created_at) "
                "VALUES (:id, :collective, :event, now())"
            ),
            {"id": participation_id, "collective": collective, "event": event_id},
        )
    return participation_id


async def _declare(
    engine: AsyncEngine,
    participation: UUID,
    member: UUID,
    is_attended: bool,
    *,
    marked: bool = True,
    verified: bool = False,
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO attendance (id, member_id, participation_id, "
                "is_attended, is_verified, created_at, edited_at) VALUES "
                "(:id, :member, :participation, :attended, :verified, "
                "now(), CASE WHEN :marked THEN now() END)"
            ),
            {
                "id": uuid4(),
                "member": member,
                "participation": participation,
                "attended": is_attended,
                "verified": verified,
                "marked": marked,
            },
        )


async def _seed(engine: AsyncEngine, size: int = 3) -> Seed:
    leader = await _person(engine, "Leader")
    collective = await _collective(engine, "Choir", leader)
    persons = [await _person(engine, f"Member{i}") for i in range(size)]
    members = [await _member(engine, person, collective) for person in persons]
    return Seed(leader, collective, members, persons)


def _url(collective: UUID) -> str:
    return f"{BASE}/{collective}/profile"


async def test_the_card_counts_the_whole_declared_roster(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    first = await _event(
        event_engine, seed.collective, "Rehearsal", -10, type="rehearsal"
    )
    second = await _event(
        event_engine, seed.collective, "Concert", -3, status="archived", type="concert"
    )
    upcoming = await _event(event_engine, seed.collective, "Next", 5)
    a, b, c = seed.members
    await _declare(event_engine, first, a, True, verified=True)
    await _declare(event_engine, first, b, False)
    await _declare(event_engine, first, c, True)
    await _declare(event_engine, second, a, True)
    await _declare(event_engine, second, b, True, marked=False)
    await _declare(event_engine, second, c, False, marked=False)
    await _declare(event_engine, upcoming, a, True)

    response = await api.get(
        _url(seed.collective),
        params={"date_from": _day(-30).isoformat(), "date_to": _day(10).isoformat()},
        headers=principal(person_id=seed.leader),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["can_manage"] is True
    assert body["collective"]["name"] == "Choir"
    assert body["collective"]["principal"]["surname"] == "Leader"
    assert body["collective"]["active_members"] == 3
    summary = body["summary"]
    assert (
        summary["attended"],
        summary["absent"],
        summary["unmarked"],
        summary["upcoming"],
    ) == (3, 1, 2, 1)
    assert summary["past"] == 6
    assert summary["verified"] == 1
    assert summary["rate"] == 0.5
    assert summary["events"] == 3
    assert [d["date"] for d in body["days"]] == [
        _day(-10).isoformat(),
        _day(-3).isoformat(),
        _day(5).isoformat(),
    ]
    by_date = {d["date"]: d for d in body["days"]}
    day = by_date[_day(-3).isoformat()]
    assert (day["attended"], day["absent"], day["unmarked"], day["upcoming"]) == (
        1,
        0,
        2,
        0,
    )
    assert [e["event_name"] for e in body["events"]] == ["Next", "Concert", "Rehearsal"]
    rehearsal = body["events"][2]
    assert (rehearsal["attended"], rehearsal["absent"]) == (2, 1)
    assert rehearsal["type"] == "rehearsal"
    assert [(t["type"], t["attended"]) for t in body["by_type"]] == [
        ("concert", 1),
        ("rehearsal", 2),
        (None, 0),
    ]
    assert sum(m["attended"] for m in body["by_month"]) == 3
    assert [m["person"]["surname"] for m in body["members"]] == [
        "Member0",
        "Member1",
        "Member2",
    ]
    first_member = body["members"][0]
    assert first_member["member_id"] == str(a)
    assert (first_member["attended"], first_member["past"], first_member["rate"]) == (
        2,
        2,
        1.0,
    )
    assert body["members"][2]["rate"] == 0.5


async def test_unmarked_rows_and_unmarked_days_are_reported_not_rated(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine, 2)
    only_unmarked = await _event(event_engine, seed.collective, "Untouched", -4)
    for member in seed.members:
        await _declare(event_engine, only_unmarked, member, False, marked=False)

    response = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )

    day = response.json()["days"][0]
    assert (day["attended"], day["absent"], day["unmarked"]) == (0, 0, 2)
    assert response.json()["summary"]["rate"] == 0.0


async def test_events_outside_the_counted_statuses_or_dates_are_left_out(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine, 1)
    member = seed.members[0]
    for name, offset, status in (
        ("Draft", -2, "draft"),
        ("Template", -2, "template"),
        ("Undated", None, "active"),
        ("Long ago", -900, "active"),
        ("Counted", -2, "active"),
    ):
        participation = await _event(
            event_engine, seed.collective, name, offset, status=status
        )
        await _declare(event_engine, participation, member, True)

    response = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )

    assert [e["event_name"] for e in response.json()["events"]] == ["Counted"]
    years = response.json()["years"]
    assert {_day(-900).year, _day(-2).year} <= set(years)


async def test_the_period_limits_the_counts_but_not_the_years(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine, 1)
    member = seed.members[0]
    for name, offset in (("Recent", -5), ("Older", -40)):
        participation = await _event(event_engine, seed.collective, name, offset)
        await _declare(event_engine, participation, member, True)

    response = await api.get(
        _url(seed.collective),
        params={"date_from": _day(-10).isoformat(), "date_to": _day(0).isoformat()},
        headers=principal(person_id=seed.leader),
    )

    assert [e["event_name"] for e in response.json()["events"]] == ["Recent"]
    assert response.json()["date_from"] == _day(-10).isoformat()


async def test_another_collectives_events_are_not_counted(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine, 1)
    other = await _collective(event_engine, "Dance", seed.leader)
    stranger = await _member(event_engine, seed.persons[0], other)
    participation = await _event(event_engine, other, "Elsewhere", -3)
    await _declare(event_engine, participation, stranger, True)

    response = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )

    assert response.json()["events"] == []
    assert response.json()["members"][0]["past"] == 0


async def test_a_member_who_left_shows_only_with_events(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine, 1)
    quiet = await _member(
        event_engine,
        await _person(event_engine, "Quiet"),
        seed.collective,
        active=False,
    )
    gone_person = await _person(event_engine, "Gone")
    gone = await _member(event_engine, gone_person, seed.collective, active=False)
    participation = await _event(event_engine, seed.collective, "Old", -8)
    await _declare(event_engine, participation, gone, True)

    response = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )

    members = {m["member_id"]: m for m in response.json()["members"]}
    assert str(quiet) not in members
    assert members[str(gone)]["is_active"] is False
    assert members[str(gone)]["attended"] == 1
    assert response.json()["collective"]["active_members"] == 1


async def test_the_leader_members_and_superusers_may_read_a_stranger_may_not(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine, 1)
    outsider = await _person(event_engine, "Outsider")
    inactive = await _person(event_engine, "Inactive")
    await _member(event_engine, inactive, seed.collective, active=False)

    leader = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.leader)
    )
    member = await api.get(
        _url(seed.collective), headers=principal(person_id=seed.persons[0])
    )
    admin = await api.get(_url(seed.collective), headers=principal(superuser=True))
    stranger = await api.get(
        _url(seed.collective), headers=principal(person_id=outsider)
    )
    left = await api.get(_url(seed.collective), headers=principal(person_id=inactive))
    unlinked = await api.get(_url(seed.collective), headers=principal())
    anonymous = await api.get(_url(seed.collective))

    assert [leader.status_code, member.status_code, admin.status_code] == [
        200,
        200,
        200,
    ]
    assert leader.json()["can_manage"] is True
    assert member.json()["can_manage"] is False
    assert admin.json()["can_manage"] is True
    assert stranger.status_code == 403
    assert stranger.json()["detail"] == "NOT_COLLECTIVE_MEMBER"
    assert left.status_code == 403
    assert unlinked.status_code == 403
    assert anonymous.status_code in (401, 403)


async def test_an_unknown_collective_is_not_found(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    response = await api.get(_url(uuid4()), headers=principal(superuser=True))

    assert response.status_code == 404
    assert response.json()["detail"] == "COLLECTIVE_NOT_FOUND"


async def test_a_malformed_period_is_rejected(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine, 1)

    half = await api.get(
        _url(seed.collective),
        params={"date_from": "2026-01-01"},
        headers=principal(superuser=True),
    )
    reversed_ = await api.get(
        _url(seed.collective),
        params={"date_from": "2026-02-01", "date_to": "2026-01-01"},
        headers=principal(superuser=True),
    )

    assert half.status_code == 422
    assert reversed_.status_code == 422
