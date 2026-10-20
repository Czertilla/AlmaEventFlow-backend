import datetime

from icalendar import Calendar, Component, Event

from .datetime_renderer import CalendarDateTimeRenderer
from .model import VEvent

PRODID = "-//AlmaEventFlow//Calendar//RU"


def _add(component: Component, name: str, value: object) -> None:
    component.add(name, value)  # pyright: ignore[reportUnknownMemberType]  # icalendar leaves `value` unannotated


class CalendarIcsRenderer:
    """Serializes the intermediate ``VEvent`` model into an ICS feed."""

    def __init__(
        self, dt_renderer: CalendarDateTimeRenderer | None = None
    ) -> None:
        self._dt = dt_renderer or CalendarDateTimeRenderer()

    def render(self, calendar_name: str, vevents: list[VEvent]) -> str:
        cal = Calendar()
        _add(cal, "prodid", PRODID)
        _add(cal, "version", "2.0")
        _add(cal, "calscale", "GREGORIAN")
        # no METHOD: it makes Apple and Google read the feed as invitations
        _add(cal, "x-wr-calname", calendar_name)
        _add(cal, "name", calendar_name)
        _add(cal, "x-published-ttl", "PT6H")
        _add(cal, "refresh-interval;value=duration", "PT6H")
        for ve in vevents:
            cal.add_component(self._event(ve))
        return cal.to_ical().decode("utf-8")

    def _event(self, ve: VEvent) -> Event:
        event = Event()
        _add(event, "uid", ve.uid)
        _add(event, "dtstamp", self._dt.to_utc(ve.dtstamp))
        _add(event, "last-modified", self._dt.to_utc(ve.last_modified))
        _add(event, "sequence", ve.sequence)
        _add(event, "summary", ve.summary)
        _add(event, "dtstart", self._value(ve.dtstart, ve.all_day))
        if ve.dtend is not None:
            _add(event, "dtend", self._value(ve.dtend, ve.all_day))
        _add(event, "status", ve.status)
        if ve.description:
            _add(event, "description", ve.description)
        if ve.location:
            _add(event, "location", ve.location)
        if ve.geo:
            _add(event, "geo", ve.geo)
        _add(event, "url", ve.url)
        if ve.categories:
            _add(event, "categories", ve.categories)
        if ve.x_status:
            _add(event, "x-almaeventflow-status", ve.x_status)
        return event

    def _value(
        self, value: datetime.date | datetime.datetime, all_day: bool
    ) -> datetime.date | datetime.datetime:
        if all_day:
            return value
        assert isinstance(value, datetime.datetime)
        return self._dt.to_utc(value)
