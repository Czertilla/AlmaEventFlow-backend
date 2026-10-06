import datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from event.service.event import EventService, EventSnapshot

LOCATION, OTHER_LOCATION = uuid4(), uuid4()
ORGANIZER, OTHER_ORGANIZER = uuid4(), uuid4()


def _event(**changes: Any) -> SimpleNamespace:
    fields: dict[str, Any] = {
        "id": uuid4(),
        "status": "active",
        "name": "Concert",
        "date": datetime.date(2026, 5, 1),
        "description": "Bring a friend",
        "location_id": LOCATION,
        "organizer_id": ORGANIZER,
        "level": "regional",
    }
    return SimpleNamespace(**(fields | changes))


class _Service(EventService):
    def __init__(self) -> None:
        super().__init__(None)  # pyright: ignore[reportArgumentType]
        self.noticed: list[UUID] = []

    async def _publish_event_notice(self, event_id: UUID) -> None:
        self.noticed.append(event_id)


async def _edit(before: SimpleNamespace, **changes: Any) -> list[UUID]:
    service = _Service()
    old = EventSnapshot.of(before)  # pyright: ignore[reportArgumentType]
    after = SimpleNamespace(**(vars(before) | changes))
    await service._publish_activation(old, after)  # pyright: ignore[reportArgumentType,reportPrivateUsage]
    return service.noticed


@pytest.mark.parametrize(
    "change",
    [
        {"name": "Gala"},
        {"date": datetime.date(2026, 5, 2)},
        {"description": "Changed the program"},
        {"description": None},
        {"location_id": OTHER_LOCATION},
        {"location_id": None},
        {"organizer_id": OTHER_ORGANIZER},
    ],
    ids=[
        "name",
        "date",
        "description",
        "description-cleared",
        "location",
        "location-cleared",
        "organizer",
    ],
)
async def test_everything_the_announcement_shows_refreshes_it_when_edited(
    change: dict[str, Any],
) -> None:
    before = _event()

    assert await _edit(before, **change) == [before.id]


@pytest.mark.parametrize(
    "change",
    [{}, {"level": "national"}, {"description": "Bring a friend"}],
    ids=["nothing", "level", "same-description"],
)
async def test_an_edit_that_changes_nothing_visible_stays_quiet(
    change: dict[str, Any],
) -> None:
    before = _event()

    assert await _edit(before, **change) == []


async def test_activating_an_event_announces_it() -> None:
    before = _event(status="draft")

    assert await _edit(before, status="active") == [before.id]


async def test_editing_an_event_that_is_not_active_stays_quiet() -> None:
    before = _event(status="draft")

    assert await _edit(before, name="Gala", description="Other") == []
