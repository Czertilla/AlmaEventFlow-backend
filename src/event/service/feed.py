import datetime
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row

from core.service.base import BaseService, required_transaction
from event.dto.feed import (
    CardParticipationDTO,
    EventCardDTO,
    FeedDTO,
    FeedParamsDTO,
    PlaceDTO,
    ViewerContextDTO,
)
from event.dto.member_profile import ProfileViewerDTO
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1
from event.service.attendance_stats import shown_attendance
from event.service.viewer import viewer_context
from event.service.window import read_window
from event.uow.view import ViewUOW


class FeedService(BaseService[ViewUOW]):
    @required_transaction
    async def _context(self, viewer: ProfileViewerDTO) -> ViewerContextDTO:
        return await viewer_context(self.uow.view, viewer)

    @required_transaction
    async def _cards(
        self, rows: Sequence[Row[Any]], context: ViewerContextDTO
    ) -> list[EventCardDTO]:
        """Cards in the order of ``rows``: the participations and the marks are the
        viewer's own, the counters are those of the whole participation."""
        feed = self.uow.view
        event_ids = [row.id for row in rows]
        collective_ids = {c.id for c in context.collectives}
        member_ids = {c.member_id for c in context.collectives if c.member_id}
        spans = await feed.stage_spans(event_ids)
        places = await feed.places({r.location_id for r in rows if r.location_id})
        participations = await feed.participations(event_ids, collective_ids)
        participation_ids = [p.id for p in participations]
        counts = await feed.attendance_counts(participation_ids)
        mine = {
            a.participation_id: shown_attendance(a)
            for a in await feed.attendances_of_members(participation_ids, member_ids)
        }
        by_event: dict[UUID, list[CardParticipationDTO]] = {}
        latest: dict[UUID, datetime.datetime] = {}
        for p in participations:
            found = counts.get(p.id)
            by_event.setdefault(p.event_id, []).append(
                CardParticipationDTO(
                    id=p.id,
                    collective_id=p.collective_id,
                    collective_name=p.collective_name,
                    attended_count=found.attended if found else 0,
                    total_count=found.total if found else 0,
                    my_attendance=mine.get(p.id),
                )
            )
            if found and found.latest:
                latest[p.event_id] = max(
                    latest.get(p.event_id, found.latest), found.latest
                )
        cards: list[EventCardDTO] = []
        for row in rows:
            place = places.get(row.location_id) if row.location_id else None
            span = spans.get(row.id)
            cards.append(
                EventCardDTO(
                    id=row.id,
                    name=row.name,
                    date=row.date,
                    status=EventStatusEnumV1(row.status),
                    level=EventLevelEnumV1(row.level) if row.level else None,
                    type=EventTypeEnumV1(row.type) if row.type else None,
                    format=row.format,
                    location=PlaceDTO(
                        id=place.id, name=place.name, lat=place.lat, lon=place.lon
                    )
                    if place is not None
                    else None,
                    starts_at=span[0] if span else None,
                    ends_at=span[1] if span else None,
                    participations=by_event.get(row.id, []),
                    created_at=row.created_at,
                    edited_at=row.edited_at,
                    updated_at=max(
                        row.edited_at or row.created_at,
                        latest.get(row.id, row.created_at),
                    ),
                )
            )
        return cards

    async def context(self, viewer: ProfileViewerDTO) -> ViewerContextDTO:
        async with self.uow:
            return await self._context(viewer)

    async def feed(self, params: FeedParamsDTO, viewer: ProfileViewerDTO) -> FeedDTO:
        async with self.uow:
            window = await read_window(
                self.uow.view,
                viewer,
                params.filters,
                direction=params.direction,
                anchor=params.anchor or datetime.date.today(),
                cursor=params.cursor,
                limit=params.limit,
            )
            items = await self._cards(window.rows, await self._context(viewer))
        return FeedDTO(
            items=items,
            has_more_past=window.has_more_past,
            has_more_future=window.has_more_future,
            past_cursor=window.past_cursor,
            future_cursor=window.future_cursor,
        )

    async def cards(
        self, event_ids: Sequence[UUID], viewer: ProfileViewerDTO
    ) -> list[EventCardDTO]:
        async with self.uow:
            rows = await self.uow.view.by_ids(viewer, event_ids)
            order = {event_id: i for i, event_id in enumerate(event_ids)}
            rows = sorted(rows, key=lambda row: order[row.id])
            return await self._cards(rows, await self._context(viewer))

    async def pending(self, viewer: ProfileViewerDTO) -> list[EventCardDTO]:
        async with self.uow:
            context = await self._context(viewer)
            member_ids = [c.member_id for c in context.collectives if c.member_id]
            event_ids = await self.uow.view.pending_event_ids(member_ids)
            rows = await self.uow.view.by_ids(viewer, event_ids)
            order = {event_id: i for i, event_id in enumerate(event_ids)}
            rows = sorted(rows, key=lambda row: order[row.id])
            return await self._cards(rows, context)
