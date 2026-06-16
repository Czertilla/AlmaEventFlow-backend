import datetime
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from event.models.event import EventORM
    from event.models.stage import EventStageORM


@dataclass
class FeedItem:
    """A visible event plus its stages and the UID owner reference."""

    event: "EventORM"
    owner_kind: str
    owner_id: UUID
    stages: list["EventStageORM"]


@dataclass
class VEvent:
    """Intermediate calendar model — independent of ICS text formatting."""

    uid: str
    summary: str
    dtstart: datetime.date | datetime.datetime
    dtend: datetime.date | datetime.datetime | None
    all_day: bool
    status: str
    url: str
    dtstamp: datetime.datetime
    last_modified: datetime.datetime
    sequence: int = 0
    description: str | None = None
    location: str | None = None
    geo: tuple[float, float] | None = None
    categories: list[str] = field(default_factory=list)
    x_status: str | None = None
