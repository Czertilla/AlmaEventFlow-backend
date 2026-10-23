from uuid import UUID

from core.dto.base import dto_from_orm
from core.service.base import BaseService
from event.dto.event_page import (
    EventPageDTO,
    PageAttendanceDTO,
    PageEventDTO,
    PageParticipationDTO,
)
from event.dto.feed import PlaceDTO, RosterMemberDTO
from event.dto.member_profile import ProfileViewerDTO
from event.dto.stage import StageDTO
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1
from event.exc.event import EventNotExistsException
from event.service.attendance_stats import shown
from event.service.viewer import roster_by_collective, roster_of, viewer_context
from event.uow.view import ViewUOW


def _addable(
    roster: list[RosterMemberDTO], declared: set[UUID]
) -> list[RosterMemberDTO]:
    return [m for m in roster if m.is_active and m.id not in declared]


class EventPageService(BaseService[ViewUOW]):
    async def read(self, event_id: UUID, viewer: ProfileViewerDTO) -> EventPageDTO:
        """The event, its stages and every participation with the places the caller
        may see: the leader and the members of a collective see its whole roster."""
        async with self.uow:
            view = self.uow.view
            rows = await view.by_ids(viewer, [event_id], templates=True)
            if not rows:
                raise EventNotExistsException()
            row = rows[0]
            context = await viewer_context(view, viewer)
            details = await view.event_details(event_id)
            places = await view.places([row.location_id] if row.location_id else [])
            place = places.get(row.location_id) if row.location_id else None
            stages = [dto_from_orm(s, StageDTO) for s in await view.stages_of(event_id)]
            participations = await view.participations([event_id], None)

            led = {c.id for c in context.collectives if c.is_principal}
            mine = {c.id: c.member_id for c in context.collectives if c.member_id}
            seen = [
                p
                for p in participations
                if viewer.is_superuser
                or p.collective_id in led
                or p.collective_id in mine
            ]
            seen_ids = [p.id for p in seen]
            attendances = await view.attendances_of(seen_ids)
            counts = await view.attendance_counts(seen_ids)
            members = await roster_of(
                view, await view.members_by_ids({a.member_id for a in attendances})
            )
            managed = [
                p.collective_id
                for p in seen
                if viewer.is_superuser or p.collective_id in led
            ]
            rosters = await roster_by_collective(view, managed)

            items: list[PageParticipationDTO] = []
            for p in participations:
                is_principal = viewer.is_superuser or p.collective_id in led
                is_member = p.collective_id in mine
                can_view = is_principal or is_member
                rows_of = sorted(
                    (a for a in attendances if a.participation_id == p.id),
                    key=lambda a: (
                        members[a.member_id].person.surname,
                        members[a.member_id].person.name,
                        str(a.id),
                    ),
                )
                declared = {a.member_id for a in rows_of}
                found = counts.get(p.id)
                attended, total = (found.attended, found.total) if found else (0, 0)
                own = mine.get(p.collective_id)
                items.append(
                    PageParticipationDTO(
                        id=p.id,
                        collective_id=p.collective_id,
                        collective_name=p.collective_name,
                        priority_degree=p.priority_degree,
                        is_principal=is_principal,
                        is_member=is_member,
                        can_view_attendances=can_view,
                        attended_count=attended if can_view else None,
                        total_count=total if can_view else None,
                        my_attendance_id=next(
                            (a.id for a in rows_of if a.member_id == own), None
                        )
                        if can_view
                        else None,
                        attendances=[
                            PageAttendanceDTO(
                                id=a.id,
                                member_id=a.member_id,
                                participation_id=a.participation_id,
                                is_attended=shown(
                                    a.is_attended, a.edited_at, a.is_verified
                                ),
                                is_verified=a.is_verified,
                                comment=a.comment,
                                created_at=a.created_at,
                                edited_at=a.edited_at,
                                member=members[a.member_id],
                            )
                            for a in rows_of
                        ]
                        if can_view
                        else [],
                        addable_members=_addable(
                            rosters.get(p.collective_id, []), declared
                        )
                        if is_principal
                        else [],
                    )
                )
            items.sort(
                key=lambda p: (
                    not p.can_view_attendances,
                    p.collective_name.lower(),
                    str(p.id),
                )
            )
            editable = next((p.collective_id for p in items if p.is_principal), None)
            return EventPageDTO(
                event=PageEventDTO(
                    id=row.id,
                    name=row.name,
                    date=row.date,
                    description=details.description,
                    status=EventStatusEnumV1(row.status),
                    level=EventLevelEnumV1(row.level) if row.level else None,
                    type=EventTypeEnumV1(row.type) if row.type else None,
                    format=row.format,
                    organizer_id=details.organizer_id,
                    location_id=row.location_id,
                    location=PlaceDTO(
                        id=place.id, name=place.name, lat=place.lat, lon=place.lon
                    )
                    if place is not None
                    else None,
                    created_at=row.created_at,
                    edited_at=row.edited_at,
                ),
                stages=stages,
                participations=items,
                editable_collective_id=editable,
            )
