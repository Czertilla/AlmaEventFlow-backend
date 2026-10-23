import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Row

from event.dto.feed import EventFilterViewDTO, EventKeyDTO, FeedDirection
from event.dto.member_profile import ProfileViewerDTO
from event.repository.view import ViewRepo


@dataclass(frozen=True, slots=True)
class Window:
    rows: list[Row[Any]]
    has_more_past: bool
    has_more_future: bool
    past_cursor: EventKeyDTO | None
    future_cursor: EventKeyDTO | None


def key_of(row: Row[Any]) -> EventKeyDTO:
    return EventKeyDTO(date=row.date, id=row.id)


async def read_window(
    view: ViewRepo,
    viewer: ProfileViewerDTO | None,
    filters: EventFilterViewDTO,
    *,
    direction: FeedDirection,
    anchor: datetime.date,
    cursor: EventKeyDTO | None,
    limit: int,
) -> Window:
    """Events in date order around ``anchor`` or next to ``cursor``, ``limit`` of each
    side asked for; the rows are ascending, whatever the side."""
    past: Sequence[Row[Any]] = []
    future: Sequence[Row[Any]] = []
    if direction is not FeedDirection.future:
        past = await view.window(
            viewer,
            filters,
            side="past",
            boundary=anchor,
            after=cursor if direction is FeedDirection.past else None,
            limit=limit,
        )
    if direction is not FeedDirection.past:
        floor = filters.date_from
        future = await view.window(
            viewer,
            filters,
            side="future",
            boundary=max(anchor, floor) if floor else anchor,
            after=cursor if direction is FeedDirection.future else None,
            limit=limit,
        )
    kept_past, kept_future = list(past[:limit]), list(future[:limit])
    return Window(
        rows=[*reversed(kept_past), *kept_future],
        has_more_past=len(past) > limit,
        has_more_future=len(future) > limit,
        past_cursor=key_of(kept_past[-1]) if kept_past else None,
        future_cursor=key_of(kept_future[-1]) if kept_future else None,
    )
