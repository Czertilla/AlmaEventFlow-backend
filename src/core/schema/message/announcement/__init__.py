from uuid import UUID

from pydantic import Field

from core.schema.message.core import MQRequest


class AnnouncementRequest(MQRequest):
    """A group-chat announcement request (``AnnouncementQueue.COLLECTIVE_REQUESTED``).
    One request per collective — a collective's official chat is resolved and
    owned entirely by ``bot``, which also decides edit-vs-send by
    ``event_id`` (the same correlation table personal Telegram deliveries
    use)."""

    collective_id: UUID
    event_id: UUID
    title: str
    body: str = ""
    action_url: str | None = None
    data: dict[str, str] = Field(
        default_factory=dict,
        description="Open-ended, e.g. event_id/event_date/stage_start_at "
        "today -- a future field like the event's location can be added "
        "the same way, without a schema migration.",
    )
