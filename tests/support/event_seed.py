import datetime
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

TODAY = datetime.date.today()


def day(offset: int) -> datetime.date:
    return TODAY + datetime.timedelta(days=offset)


def iso(offset: int) -> str:
    return day(offset).isoformat()


async def person(
    engine: AsyncEngine,
    surname: str = "Doe",
    name: str = "Ivan",
    patronymic: str | None = None,
) -> UUID:
    person_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO person (id, surname, name, patronymic) "
                "VALUES (:id, :surname, :name, :patronymic)"
            ),
            {
                "id": person_id,
                "surname": surname,
                "name": name,
                "patronymic": patronymic,
            },
        )
    return person_id


async def collective(
    engine: AsyncEngine,
    name: str = "Choir",
    leader: UUID | None = None,
    *,
    verified: bool = True,
) -> UUID:
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
            text("INSERT INTO collective (id, is_verified) VALUES (:id, :verified)"),
            {"id": collective_id, "verified": verified},
        )
    return collective_id


async def member(
    engine: AsyncEngine, person_id: UUID, collective_id: UUID, *, active: bool = True
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
                "person": person_id,
                "collective": collective_id,
                "active": active,
            },
        )
    return member_id


async def role(
    engine: AsyncEngine,
    collective_id: UUID,
    name: str,
    members: list[UUID] | None = None,
) -> UUID:
    role_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO role (id, collective_id, name, created_at) "
                "VALUES (:id, :collective, :name, now())"
            ),
            {"id": role_id, "collective": collective_id, "name": name},
        )
        for member_id in members or []:
            await conn.execute(
                text("INSERT INTO member_role (role_id, member_id) VALUES (:r, :m)"),
                {"r": role_id, "m": member_id},
            )
    return role_id


async def location(
    engine: AsyncEngine,
    name: str | None = "Hall",
    lat: float | None = 55.75,
    lon: float | None = 37.61,
) -> UUID:
    location_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO location (id, name, lat, lon) "
                "VALUES (:id, :name, :lat, :lon)"
            ),
            {"id": location_id, "name": name, "lat": lat, "lon": lon},
        )
    return location_id


@dataclass
class Seeded:
    id: UUID
    participations: dict[UUID, UUID] = field(default_factory=lambda: {})

    def of(self, collective_id: UUID) -> UUID:
        return self.participations[collective_id]


async def event(
    engine: AsyncEngine,
    name: str,
    on: datetime.date | None,
    collectives: list[UUID],
    *,
    status: str = "active",
    type: str | None = None,
    level: str | None = None,
    format: str = "offline",
    location_id: UUID | None = None,
    event_id: UUID | None = None,
) -> Seeded:
    seeded = Seeded(id=event_id or uuid4())
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO event (id, name, date, status_id, type_id, level_id, "
                "format, location_id, created_at) VALUES (:id, :name, :date, "
                "(SELECT id FROM event_status WHERE name = :status), "
                "(SELECT id FROM event_type WHERE name = :type), "
                "(SELECT id FROM event_level WHERE name = :level), "
                "CAST(:format AS event_format), :location, now())"
            ),
            {
                "id": seeded.id,
                "name": name,
                "date": on,
                "status": status,
                "type": type,
                "level": level,
                "format": format,
                "location": location_id,
            },
        )
        for collective_id in collectives:
            participation_id = uuid4()
            seeded.participations[collective_id] = participation_id
            await conn.execute(
                text(
                    "INSERT INTO participation "
                    "(id, collective_id, event_id, created_at) "
                    "VALUES (:id, :collective, :event, now())"
                ),
                {
                    "id": participation_id,
                    "collective": collective_id,
                    "event": seeded.id,
                },
            )
    return seeded


async def stage(
    engine: AsyncEngine,
    event_id: UUID,
    start: datetime.datetime,
    end: datetime.datetime | None = None,
    name: str = "Stage",
) -> UUID:
    stage_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO event_stage "
                "(id, event_id, name, start_at, end_at, created_at) "
                "VALUES (:id, :event, :name, :start, :end, now())"
            ),
            {
                "id": stage_id,
                "event": event_id,
                "name": name,
                "start": start,
                "end": end,
            },
        )
    return stage_id


async def attendance(
    engine: AsyncEngine,
    participation_id: UUID,
    member_id: UUID,
    is_attended: bool = False,
    *,
    marked: bool = False,
    verified: bool = False,
    comment: str | None = None,
) -> UUID:
    attendance_id = uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO attendance (id, member_id, participation_id, is_attended, "
                "is_verified, comment, created_at, edited_at) VALUES (:id, :member, "
                ":participation, :attended, :verified, :comment, now(), "
                "CASE WHEN :marked THEN now() END)"
            ),
            {
                "id": attendance_id,
                "member": member_id,
                "participation": participation_id,
                "attended": is_attended,
                "verified": verified,
                "comment": comment,
                "marked": marked,
            },
        )
    return attendance_id
