import datetime
from uuid import uuid4

from event.models.event import EventORM
from event.models.location import LocationORM
from event.models.stage import EventStageORM
from event.service.calendar.mapper import CalendarEventMapper
from event.service.calendar.model import FeedItem


def _event(**kwargs) -> EventORM:
    return EventORM(
        id=uuid4(), name="Concert", date=datetime.date(2026, 5, 1), **kwargs
    )


def _item(event: EventORM, stages: list[EventStageORM] | None = None) -> FeedItem:
    return FeedItem(
        event=event, owner_kind="attendance", owner_id=uuid4(), stages=stages or []
    )


def test_all_day_event_carries_its_location_name():
    event = _event(location=LocationORM(id=uuid4(), name="Ленина, 10"))

    vevents = CalendarEventMapper().map_items([_item(event)])

    assert len(vevents) == 1
    assert vevents[0].location == "Ленина, 10"


def test_event_without_a_location_has_no_ics_location():
    vevents = CalendarEventMapper().map_items([_item(_event())])

    assert vevents[0].location is None


def test_single_stage_event_carries_its_location_name():
    event = _event(location=LocationORM(id=uuid4(), name="Ленина, 10"))
    stage = EventStageORM(
        id=uuid4(),
        event_id=event.id,
        name="Выступление",
        start_at=datetime.datetime(2026, 5, 1, 18, 0, tzinfo=datetime.UTC),
    )

    vevents = CalendarEventMapper().map_items([_item(event, [stage])])

    assert len(vevents) == 1
    assert vevents[0].location == "Ленина, 10"
