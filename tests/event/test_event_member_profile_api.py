import datetime
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from support.http import principal

BASE = "/event/v2/members"
TODAY = datetime.date.today()


def _day(offset: int) -> str:
    return (TODAY + datetime.timedelta(days=offset)).isoformat()


@dataclass
class Seed:
    leader: UUID
    person: UUID
    collective: UUID
    member: UUID


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


async def _attend(
    engine: AsyncEngine,
    *,
    member: UUID,
    collective: UUID,
    name: str,
    offset: int | None,
    is_attended: bool | None,
    marked: bool = True,
    status: str = "active",
    type: str | None = None,
    verified: bool = False,
    comment: str | None = None,
    date: str | None = None,
) -> None:
    event_id, participation_id = uuid4(), uuid4()
    when = date or (_day(offset) if offset is not None else None)
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
                "date": datetime.date.fromisoformat(when) if when else None,
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
        await conn.execute(
            text(
                "INSERT INTO attendance (id, member_id, participation_id, "
                "is_attended, is_verified, comment, created_at, edited_at) VALUES "
                "(:id, :member, :participation, :attended, :verified, :comment, "
                "now(), CASE WHEN :marked THEN now() END)"
            ),
            {
                "id": uuid4(),
                "member": member,
                "participation": participation_id,
                "attended": is_attended,
                "verified": verified,
                "comment": comment,
                "marked": marked,
            },
        )


async def _seed(engine: AsyncEngine) -> Seed:
    leader = await _person(engine, "Leader")
    collective = await _collective(engine, "Choir", leader)
    person = await _person(engine, "Petrov")
    member = await _member(engine, person, collective)
    return Seed(leader, person, collective, member)


def _url(seed: Seed, member: UUID | None = None) -> str:
    return f"{BASE}/{member or seed.member}/profile"


async def test_leader_reads_the_card_and_attendance_statistics(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    kw: dict[str, Any] = {"member": seed.member, "collective": seed.collective}
    await _attend(event_engine, name="Rehearsal 1", offset=-20, is_attended=True,
                  type="rehearsal", verified=True, **kw)
    await _attend(event_engine, name="Rehearsal 2", offset=-10, is_attended=False,
                  type="rehearsal", comment="Ill", **kw)
    await _attend(event_engine, name="Concert", offset=-5, is_attended=True,
                  type="concert", status="archived", **kw)
    await _attend(event_engine, name="Untouched", offset=-4, is_attended=False,
                  marked=False, **kw)
    await _attend(event_engine, name="Forgotten", offset=-3, is_attended=None, **kw)
    await _attend(event_engine, name="Next", offset=7, is_attended=True, **kw)
    await _attend(event_engine, name="Draft", offset=-2, is_attended=True,
                  status="draft", **kw)
    await _attend(event_engine, name="Template", offset=-2, is_attended=True,
                  status="template", **kw)
    await _attend(event_engine, name="Undated", offset=None, is_attended=True, **kw)
    await _attend(event_engine, name="Long ago", offset=None, is_attended=True,
                  date="2019-05-01", **kw)

    response = await api.get(_url(seed), headers=principal(person_id=seed.leader))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["person"]["surname"] == "Petrov"
    assert body["can_manage"] is True
    assert body["member"]["id"] == str(seed.member)
    assert body["member"]["collective_id"] == str(seed.collective)
    assert body["date_to"] == _day(0)
    assert body["date_from"] == _day(-364)
    counted_years = {
        (TODAY + datetime.timedelta(days=offset)).year
        for offset in (-20, -10, -5, -4, -3, 7)
    }
    assert body["years"] == sorted(counted_years | {2019}, reverse=True)
    assert [i["event_name"] for i in body["items"]] == [
        "Forgotten", "Untouched", "Concert", "Rehearsal 2", "Rehearsal 1",
    ]
    assert [i["outcome"] for i in body["items"]] == [
        "unmarked", "unmarked", "attended", "absent", "attended",
    ]
    assert [i["is_attended"] for i in body["items"]] == [None, None, True, False, True]
    summary = body["summary"]
    assert (summary["attended"], summary["absent"], summary["unmarked"],
            summary["upcoming"]) == (2, 1, 2, 0)
    assert summary["past"] == 5
    assert summary["verified"] == 1
    assert summary["rate"] == 0.4
    assert summary["current_streak"] == 0
    assert summary["longest_streak"] == 1
    assert summary["last_attended"] == _day(-5)
    assert [(t["type"], t["attended"], t["absent"]) for t in body["by_type"]] == [
        ("rehearsal", 1, 1), ("concert", 1, 0), (None, 0, 0),
    ]
    assert sum(m["attended"] for m in body["by_month"]) == 2
    commented = next(i for i in body["items"] if i["event_name"] == "Rehearsal 2")
    assert commented["comment"] == "Ill"


async def test_a_row_nobody_edited_is_not_marked_whatever_is_stored(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    kw: dict[str, Any] = {"member": seed.member, "collective": seed.collective}
    await _attend(event_engine, name="Hand marked absent", offset=-6,
                  is_attended=False, **kw)
    await _attend(event_engine, name="Created present", offset=-5, is_attended=True,
                  marked=False, **kw)
    await _attend(event_engine, name="Verified", offset=-4, is_attended=False,
                  marked=False, verified=True, **kw)

    response = await api.get(_url(seed), headers=principal(person_id=seed.leader))

    by_name = {i["event_name"]: i for i in response.json()["items"]}
    assert by_name["Hand marked absent"]["outcome"] == "absent"
    assert by_name["Created present"]["outcome"] == "unmarked"
    assert by_name["Created present"]["is_attended"] is None
    assert by_name["Verified"]["outcome"] == "absent"
    assert by_name["Verified"]["is_attended"] is False


async def test_todays_and_future_events_stay_upcoming_until_marked_or_over(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    kw: dict[str, Any] = {"member": seed.member, "collective": seed.collective}
    await _attend(event_engine, name="Today done", offset=0, is_attended=True, **kw)
    await _attend(event_engine, name="Today absent", offset=0, is_attended=False, **kw)
    await _attend(event_engine, name="Today open", offset=0, is_attended=False,
                  marked=False, **kw)
    await _attend(event_engine, name="Going", offset=3, is_attended=True, **kw)
    await _attend(event_engine, name="Yesterday", offset=-1, is_attended=False, **kw)
    await _attend(event_engine, name="Yesterday open", offset=-1, is_attended=False,
                  marked=False, **kw)

    response = await api.get(
        _url(seed),
        params={"date_from": _day(-30), "date_to": _day(10)},
        headers=principal(person_id=seed.leader),
    )

    by_name = {i["event_name"]: i["outcome"] for i in response.json()["items"]}
    assert by_name == {
        "Going": "upcoming",
        "Today open": "upcoming",
        "Today done": "attended",
        "Today absent": "absent",
        "Yesterday": "absent",
        "Yesterday open": "unmarked",
    }
    assert response.json()["summary"]["upcoming"] == 2
    assert response.json()["summary"]["past"] == 4


async def test_the_period_limits_the_statistics_but_not_the_years(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    kw: dict[str, Any] = {"member": seed.member, "collective": seed.collective}
    await _attend(event_engine, name="Old", offset=None, is_attended=True,
                  date="2024-03-10", **kw)
    await _attend(event_engine, name="Older", offset=None, is_attended=False,
                  date="2023-03-10", **kw)

    response = await api.get(
        _url(seed),
        params={"date_from": "2024-01-01", "date_to": "2024-12-31"},
        headers=principal(person_id=seed.leader),
    )

    body = response.json()
    assert [i["event_name"] for i in body["items"]] == ["Old"]
    assert body["summary"]["attended"] == 1
    assert body["years"] == [2024, 2023]
    assert (body["date_from"], body["date_to"]) == ("2024-01-01", "2024-12-31")


async def test_the_leader_the_collective_and_superusers_may_read_a_stranger_may_not(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    colleague = await _person(event_engine, "Colleague")
    await _member(event_engine, colleague, seed.collective)
    former = await _person(event_engine, "Former")
    await _member(event_engine, former, seed.collective, active=False)
    other_leader = await _person(event_engine, "Other")
    other = await _collective(event_engine, "Orchestra", other_leader)
    outsider = await _person(event_engine, "Outsider")
    await _member(event_engine, outsider, other)
    nobody = await _person(event_engine, "Nobody")

    async def get(**who: Any) -> httpx.Response:
        return await api.get(_url(seed), headers=principal(**who))

    by_leader = await get(person_id=seed.leader)
    by_self = await get(person_id=seed.person)
    by_colleague = await get(person_id=colleague)
    by_admin = await get(superuser=True)
    by_former = await get(person_id=former)
    by_outsider = await get(person_id=outsider)
    by_other_leader = await get(person_id=other_leader)
    by_nobody = await get(person_id=nobody)
    by_account_without_person = await get()
    anonymous = await api.get(_url(seed))

    allowed = (by_leader, by_self, by_colleague, by_admin)
    assert [r.status_code for r in allowed] == [200] * 4
    assert [r.json()["can_manage"] for r in allowed] == [True, False, False, True]
    for denied in (by_former, by_outsider, by_other_leader, by_nobody,
                   by_account_without_person):
        assert denied.status_code == 403
        assert denied.json()["detail"] == "NOT_COLLECTIVE_MEMBER"
    assert anonymous.status_code == 401


async def test_comments_are_shown_to_the_leader_and_the_member_only(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    colleague = await _person(event_engine, "Colleague")
    await _member(event_engine, colleague, seed.collective)
    await _attend(event_engine, member=seed.member, collective=seed.collective,
                  name="Rehearsal", offset=-3, is_attended=False, comment="Ill")

    async def comment(person: UUID) -> str | None:
        response = await api.get(_url(seed), headers=principal(person_id=person))
        assert response.status_code == 200
        return response.json()["items"][0]["comment"]

    assert await comment(seed.leader) == "Ill"
    assert await comment(seed.person) == "Ill"
    assert await comment(colleague) is None


async def test_an_unknown_member_is_not_found(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)

    missing = await api.get(
        _url(seed, uuid4()), headers=principal(person_id=seed.leader)
    )

    assert missing.status_code == 404


async def test_attendance_through_another_collective_is_not_counted(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    other = await _collective(event_engine, "Orchestra", seed.leader)
    await _attend(event_engine, member=seed.member, collective=other,
                  name="Foreign", offset=-3, is_attended=True)

    response = await api.get(_url(seed), headers=principal(person_id=seed.leader))

    assert response.json()["items"] == []
    assert response.json()["summary"]["rate"] is None
    assert response.json()["years"] == []


async def test_a_malformed_period_is_rejected(
    api: httpx.AsyncClient, event_engine: AsyncEngine
) -> None:
    seed = await _seed(event_engine)
    headers = principal(person_id=seed.leader)

    only_from = await api.get(
        _url(seed), params={"date_from": "2024-01-01"}, headers=headers
    )
    reversed_ = await api.get(
        _url(seed),
        params={"date_from": "2024-02-01", "date_to": "2024-01-01"},
        headers=headers,
    )
    too_long = await api.get(
        _url(seed),
        params={"date_from": "2020-01-01", "date_to": "2024-01-01"},
        headers=headers,
    )

    assert only_from.status_code == 422
    assert reversed_.status_code == 422
    assert too_long.status_code == 422
