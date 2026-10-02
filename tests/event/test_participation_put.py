from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from event.dto.participation import ParticipationPutDTO
from event.enum.priority import EventPriorityEnumV1
from event.exc.event import ParticipationNotExistsException
from event.service.participation import ParticipationService


class Repo:
    def __init__(self, row: Any) -> None:
        self.row = row
        self.calls: list[tuple[Any, dict[str, Any]]] = []

    async def update_one(
        self, id: Any, data: dict[str, Any], flush: bool = False
    ) -> Any:
        self.calls.append((id, data))
        return self.row


class UoW:
    def __init__(self, row: Any) -> None:
        self.participations = Repo(row)
        self.committed = False

    async def __aenter__(self) -> "UoW":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def is_transacting(self) -> bool:
        return True

    async def commit(self) -> None:
        self.committed = True


async def test_put_replaces_the_fields_and_returns_the_participation():
    participation_id, event_id, collective_id = uuid4(), uuid4(), uuid4()
    row = SimpleNamespace(
        id=participation_id,
        event_id=event_id,
        collective_id=collective_id,
        priority_degree=EventPriorityEnumV1.low,
        collective=None,
    )
    uow = UoW(row)

    result = await ParticipationService(uow).put(
        ParticipationPutDTO(
            id=participation_id,
            event_id=event_id,
            priority_degree=EventPriorityEnumV1.low,
        )
    )

    assert uow.participations.calls == [
        (
            participation_id,
            {"event_id": event_id, "priority_degree": EventPriorityEnumV1.low},
        )
    ]
    assert uow.committed
    assert result.id == participation_id
    assert result.priority_degree == EventPriorityEnumV1.low


async def test_put_of_a_missing_participation_raises_not_exists():
    with pytest.raises(ParticipationNotExistsException):
        await ParticipationService(UoW(None)).put(
            ParticipationPutDTO(id=uuid4(), event_id=uuid4())
        )
