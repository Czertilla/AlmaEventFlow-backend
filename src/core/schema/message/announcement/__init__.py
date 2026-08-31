from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from core.schema.message.core import MQRequest


class AnnouncementStage(MQRequest):
    name: str
    start_at: datetime
    end_at: datetime | None = None
    description: str | None = None
    timezone: str | None = None
    """IANA zone name of the client that created the stage -- ``start_at``/
    ``end_at`` are absolute UTC instants, but only this field lets a
    fixed-zone display (Telegram's plain text) show the time the creator
    actually meant."""


class AnnouncementRequest(MQRequest):
    """A group-chat announcement request (``AnnouncementQueue.COLLECTIVE_REQUESTED``).
    One request per collective — a collective's official chat is resolved and
    owned entirely by ``bot``, which also decides edit-vs-send by
    ``event_id`` (the same correlation table personal Telegram deliveries
    use).

    Carries raw structured data only -- no pre-rendered text. ``bot`` builds
    the actual message itself (i18n + templates), so it stays free to change
    layout/formatting/language without ``event`` needing to know about it."""

    collective_id: UUID
    event_id: UUID
    event_name: str
    event_date: date | None = None
    event_description: str | None = None
    location: str | None = None
    organizer: str | None = None
    stages: list[AnnouncementStage] = Field(default_factory=list)
    action_url: str | None = None
