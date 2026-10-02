from uuid import UUID, uuid4

from sqlalchemy import text

from event.dto.participation import (
    ParticipationCreateDTO,
    ParticipationPatchDTO,
    ParticipationPutDTO,
)
from event.enum.priority import EventPriorityEnumV1
from event.service.participation import ParticipationService
from event.uow.participation import ParticipationUOW


async def _seed(engine) -> tuple[UUID, UUID, UUID]:
    collective_id, event_id, participation_id = uuid4(), uuid4(), uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO event_status (id, name) VALUES (1, 's') "
                "ON CONFLICT DO NOTHING"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO organization (id, name, type) "
                "VALUES (:id, 'Choir', 'collective')"
            ),
            {"id": collective_id},
        )
        await conn.execute(
            text("INSERT INTO collective (id, is_verified) VALUES (:id, true)"),
            {"id": collective_id},
        )
        await conn.execute(
            text(
                "INSERT INTO event (id, name, status_id, created_at) "
                "VALUES (:id, 'Concert', 1, now())"
            ),
            {"id": event_id},
        )
        await conn.execute(
            text(
                "INSERT INTO participation "
                "(id, collective_id, event_id, priority_degree) "
                "VALUES (:id, :collective, :event, 'low')"
            ),
            {"id": participation_id, "collective": collective_id, "event": event_id},
        )
    return collective_id, event_id, participation_id


async def test_put_replaces_the_priority_and_names_the_collective(
    event_engine, event_sessionmaker
):
    collective_id, event_id, participation_id = await _seed(event_engine)
    service = ParticipationService(ParticipationUOW(event_sessionmaker))

    result = await service.put(
        ParticipationPutDTO(
            id=participation_id,
            event_id=event_id,
            priority_degree=EventPriorityEnumV1.hight,
        )
    )

    assert result.collective_id == collective_id
    assert result.priority_degree == EventPriorityEnumV1.hight
    assert result.collective_name == "Choir"
    stored = await service.read(participation_id)
    assert stored.priority_degree == EventPriorityEnumV1.hight


async def test_patch_clears_the_priority_when_it_is_sent_as_null(
    event_engine, event_sessionmaker
):
    _, _, participation_id = await _seed(event_engine)
    service = ParticipationService(ParticipationUOW(event_sessionmaker))

    result = await service.patch(
        ParticipationPatchDTO(
            id=participation_id,
            priority_degree=None,
            fields_set=frozenset({"priority_degree"}),
        )
    )

    assert result.priority_degree is None
    assert (await service.read(participation_id)).priority_degree is None


async def test_create_names_the_collective(event_engine, event_sessionmaker):
    collective_id, _, _ = await _seed(event_engine)
    other_event = uuid4()
    async with event_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO event (id, name, status_id, created_at) "
                "VALUES (:id, 'Other', 1, now())"
            ),
            {"id": other_event},
        )
    service = ParticipationService(ParticipationUOW(event_sessionmaker))

    result = await service.create(
        ParticipationCreateDTO(event_id=other_event, collective_id=collective_id)
    )

    assert result.collective_name == "Choir"
