import datetime

from core.config.settings import settings
from event.enum.status import EventStatusEnumV1
from event.models.calendar import CalendarChangeLogORM
from event.models.event import EventORM
from event.models.stage import EventStageORM
from .model import FeedItem, VEvent

UID_DOMAIN = "almaeventflow.ru"

OWNER_ATTENDANCE = "attendance"
OWNER_PARTICIPATION = "participation"

_OPEN_LINE = "Открыть в AlmaEventFlow: {url}"


class CalendarEventMapper:
    """Turns visible events / stages / change-log rows into ``VEvent`` objects.

    Applies the 0 / 1 / many stage layout, stable per-owner UIDs and the event
    status to ICS status mapping.
    """

    def __init__(self, now: datetime.datetime | None = None) -> None:
        self._now = now or datetime.datetime.now(datetime.timezone.utc)
        self._base_url = settings.FRONTEND_URL.rstrip("/")

    def map_items(self, items: list[FeedItem]) -> list[VEvent]:
        vevents: list[VEvent] = []
        for item in items:
            vevents.extend(self._map_item(item))
        return vevents

    def map_removed(
        self, logs: list[CalendarChangeLogORM]
    ) -> list[VEvent]:
        out: list[VEvent] = []
        for log in logs:
            out.append(self._map_removed_log(log))
        return out

    def _map_item(self, item: FeedItem) -> list[VEvent]:
        stages = sorted(item.stages, key=lambda s: s.start_at)
        if not stages:
            return [self._all_day(item, with_stages=False)]
        if len(stages) == 1:
            return [self._timed(item, stages[0], standalone=True)]
        result = [self._all_day(item, with_stages=True)]
        result.extend(
            self._timed(item, stage, standalone=False) for stage in stages
        )
        return result

    def _all_day(self, item: FeedItem, *, with_stages: bool) -> VEvent:
        event = item.event
        suffix = "-summary" if with_stages else ""
        uid = self._uid(item, event, stage_id=None, summary=with_stages)
        if with_stages:
            body = "Мероприятие содержит несколько этапов."
        else:
            body = event.description or ""
        dtstart = event.date
        dtend = (event.date + datetime.timedelta(days=1)) if event.date else None
        return self._build(
            event,
            uid=uid,
            summary=self._summary(event),
            dtstart=dtstart,
            dtend=dtend,
            all_day=True,
            description=self._description([body]),
        )

    def _timed(
        self, item: FeedItem, stage: EventStageORM, *, standalone: bool
    ) -> VEvent:
        event = item.event
        uid = self._uid(item, event, stage_id=stage.id, summary=False)
        if standalone:
            summary = self._summary(event)
            parts = [
                f"Этап: {stage.name}" if stage.name else "",
                event.description or "",
            ]
        else:
            summary = self._summary(event, stage_name=stage.name)
            parts = [stage.description or ""]
        return self._build(
            event,
            uid=uid,
            summary=summary,
            dtstart=stage.start_at,
            dtend=stage.end_at,
            all_day=False,
            description=self._description(parts),
        )

    def _map_removed_log(self, log: CalendarChangeLogORM) -> VEvent:
        url = self._event_url(log.event_id)
        dtstart = log.event_date
        dtend = (
            log.event_date + datetime.timedelta(days=1)
            if log.event_date
            else None
        )
        owner = log.participation_id or log.event_id
        uid = (
            f"almaeventflow-participation-{owner}"
            f"-event-{log.event_id}@{UID_DOMAIN}"
        )
        prefix = "[Удалено из коллектива] "
        return VEvent(
            uid=uid,
            summary=f"{prefix}{log.event_name}",
            dtstart=dtstart or self._now.date(),
            dtend=dtend,
            all_day=True,
            status="CANCELLED",
            url=url,
            dtstamp=self._now,
            last_modified=log.occurred_at,
            sequence=int(log.occurred_at.timestamp()),
            description=self._description(
                ["Мероприятие удалено из коллектива в AlmaEventFlow."], url=url
            ),
            x_status="REMOVED_FROM_COLLECTIVE",
        )

    def _build(
        self,
        event: EventORM,
        *,
        uid: str,
        summary: str,
        dtstart,
        dtend,
        all_day: bool,
        description: str,
    ) -> VEvent:
        status_value = event.status
        ics_status, categories, x_status = self._status_mapping(status_value)
        last_modified = event.edited_at or event.created_at or self._now
        sequence = (
            int(event.edited_at.timestamp()) if event.edited_at else 0
        )
        return VEvent(
            uid=uid,
            summary=summary,
            dtstart=dtstart,
            dtend=dtend,
            all_day=all_day,
            status=ics_status,
            url=self._event_url(event.id),
            dtstamp=self._now,
            last_modified=last_modified,
            sequence=sequence,
            description=self._description_with_url(description, event.id),
            categories=categories,
            x_status=x_status,
        )

    def _summary(self, event: EventORM, stage_name: str | None = None) -> str:
        base = event.name
        if stage_name:
            base = f"{base} — {stage_name}"
        status_value = event.status
        if status_value == EventStatusEnumV1.draft.value:
            return f"[Черновик] {base}"
        if status_value == EventStatusEnumV1.archived.value:
            return f"[Архив] {base}"
        return base

    @staticmethod
    def _status_mapping(
        status_value: str,
    ) -> tuple[str, list[str], str | None]:
        if status_value == EventStatusEnumV1.draft.value:
            return "TENTATIVE", ["DRAFT"], "DRAFT"
        if status_value == EventStatusEnumV1.archived.value:
            return "CANCELLED", ["ARCHIVED"], "ARCHIVED"
        return "CONFIRMED", [], None

    def _uid(
        self,
        item: FeedItem,
        event: EventORM,
        *,
        stage_id,
        summary: bool,
    ) -> str:
        prefix = f"almaeventflow-{item.owner_kind}-{item.owner_id}-event-{event.id}"
        if stage_id is not None:
            prefix = f"{prefix}-stage-{stage_id}"
        elif summary:
            prefix = f"{prefix}-summary"
        return f"{prefix}@{UID_DOMAIN}"

    def _event_url(self, event_id) -> str:
        return f"{self._base_url}/event/{event_id}"

    def _description(self, parts: list[str], url: str | None = None) -> str:
        body = "\n\n".join(p for p in parts if p)
        if url is not None:
            open_line = _OPEN_LINE.format(url=url)
            return f"{body}\n\n{open_line}" if body else open_line
        return body

    def _description_with_url(self, body: str, event_id) -> str:
        url = self._event_url(event_id)
        open_line = _OPEN_LINE.format(url=url)
        return f"{body}\n\n{open_line}" if body else open_line
