import datetime

from icalendar import Calendar, Event

from .datetime_renderer import CalendarDateTimeRenderer
from .model import VEvent

PRODID = "-//AlmaEventFlow//Calendar//RU"


class CalendarIcsRenderer:
    """Serializes the intermediate ``VEvent`` model into an ICS feed."""

    def __init__(
        self, dt_renderer: CalendarDateTimeRenderer | None = None
    ) -> None:
        self._dt = dt_renderer or CalendarDateTimeRenderer()

    def render(self, calendar_name: str, vevents: list[VEvent]) -> str:
        cal = Calendar()
        cal.add("prodid", PRODID)
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        # No METHOD: this is a subscription feed, not an iTIP scheduling
        # message. METHOD:PUBLISH makes some clients (Apple, Google) treat the
        # object as invitations and skip rendering the events.
        cal.add("x-wr-calname", calendar_name)
        cal.add("name", calendar_name)
        cal.add("x-published-ttl", "PT6H")
        cal.add("refresh-interval;value=duration", "PT6H")
        for ve in vevents:
            cal.add_component(self._event(ve))
        return cal.to_ical().decode("utf-8")

    def _event(self, ve: VEvent) -> Event:
        event = Event()
        event.add("uid", ve.uid)
        event.add("dtstamp", self._dt.to_utc(ve.dtstamp))
        event.add("last-modified", self._dt.to_utc(ve.last_modified))
        event.add("sequence", ve.sequence)
        event.add("summary", ve.summary)
        event.add("dtstart", self._value(ve.dtstart, ve.all_day))
        if ve.dtend is not None:
            event.add("dtend", self._value(ve.dtend, ve.all_day))
        event.add("status", ve.status)
        if ve.description:
            event.add("description", ve.description)
        if ve.location:
            event.add("location", ve.location)
        if ve.geo:
            event.add("geo", ve.geo)
        event.add("url", ve.url)
        if ve.categories:
            event.add("categories", ve.categories)
        if ve.x_status:
            event.add("x-almaeventflow-status", ve.x_status)
        return event

    def _value(
        self, value: datetime.date | datetime.datetime, all_day: bool
    ) -> datetime.date | datetime.datetime:
        if all_day:
            return value
        return self._dt.to_utc(value)
