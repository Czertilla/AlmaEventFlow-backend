import datetime
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Row

from core.dto.base import dto_from_orm
from core.service.base import BaseService, required_transaction
from event.dto.feed import EventFilterViewDTO, FeedDirection, PlaceDTO
from event.dto.matrix import (
    CollectiveEventDTO,
    CollectiveEventsDTO,
    MatrixDTO,
    MatrixParamsDTO,
    RosterDTO,
)
from event.dto.role import RoleDTO
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1
from event.service.attendance_stats import shown_attendance
from event.service.viewer import roster_by_collective
from event.service.window import read_window
from event.uow.view import ViewUOW

MAX_RANGE_EVENTS = 500
MAX_COLLECTIVE_EVENTS = 1000


class CollectiveViewService(BaseService[ViewUOW]):
    """What the panel of a collective's leader shows; the caller has been checked."""

    @required_transaction
    async def _roster(self, collective_id: UUID) -> RosterDTO:
        members = (await roster_by_collective(self.uow.view, [collective_id]))[
            collective_id
        ]
        roles = await self.uow.view.roles_of_collective(collective_id)
        return RosterDTO(
            members=members, roles=[dto_from_orm(r, RoleDTO) for r in roles]
        )

    @required_transaction
    async def _events(
        self, collective_id: UUID, rows: Sequence[Row[Any]]
    ) -> tuple[list[CollectiveEventDTO], list[UUID]]:
        view = self.uow.view
        event_ids = [row.id for row in rows]
        participation_of = {
            p.event_id: p.id
            for p in await view.participations(event_ids, [collective_id])
        }
        places = await view.places(
            {r.location_id for r in rows if r.location_id}
        )
        events = [
            CollectiveEventDTO(
                id=row.id,
                name=row.name,
                date=row.date,
                status=EventStatusEnumV1(row.status),
                level=EventLevelEnumV1(row.level) if row.level else None,
                type=EventTypeEnumV1(row.type) if row.type else None,
                format=row.format,
                location=PlaceDTO(
                    id=row.location_id,
                    name=places[row.location_id].name,
                    lat=places[row.location_id].lat,
                    lon=places[row.location_id].lon,
                )
                if row.location_id in places
                else None,
                participation_id=participation_of[row.id],
                created_at=row.created_at,
                edited_at=row.edited_at,
            )
            for row in rows
            if row.id in participation_of
        ]
        return events, [e.participation_id for e in events]

    async def roster(self, collective_id: UUID) -> RosterDTO:
        async with self.uow:
            return await self._roster(collective_id)

    async def events(self, collective_id: UUID) -> CollectiveEventsDTO:
        async with self.uow:
            rows = await self.uow.view.collective_events(
                collective_id, MAX_COLLECTIVE_EVENTS
            )
            events, _ = await self._events(
                collective_id, rows[:MAX_COLLECTIVE_EVENTS]
            )
            return CollectiveEventsDTO(
                items=events, truncated=len(rows) > MAX_COLLECTIVE_EVENTS
            )

    async def matrix(
        self, collective_id: UUID, params: MatrixParamsDTO
    ) -> MatrixDTO:
        """Declared places of the events in a window, with the whole roster. Given both
        ends of a range the window is the range (up to ``MAX_RANGE_EVENTS`` events)."""
        ranged = params.date_from is not None and params.date_to is not None
        filters = EventFilterViewDTO(
            collective_ids=[collective_id],
            date_from=params.date_from,
            date_to=params.date_to,
        )
        async with self.uow:
            window = await read_window(
                self.uow.view,
                None,
                filters,
                direction=FeedDirection.future if ranged else params.direction,
                anchor=(params.date_from if ranged else params.anchor)
                or datetime.date.today(),
                cursor=None if ranged else params.cursor,
                limit=MAX_RANGE_EVENTS if ranged else params.limit,
            )
            events, participation_ids = await self._events(
                collective_id, window.rows
            )
            attendances = await self.uow.view.attendances_of(participation_ids)
            roster = await self._roster(collective_id)
            return MatrixDTO(
                members=roster.members,
                roles=roster.roles,
                events=events,
                attendances=[shown_attendance(a) for a in attendances],
                has_more_past=False if ranged else window.has_more_past,
                has_more_future=window.has_more_future,
                past_cursor=None if ranged else window.past_cursor,
                future_cursor=None if ranged else window.future_cursor,
            )
