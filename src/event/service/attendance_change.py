from uuid import UUID

from core.dto.base import dto_dict
from core.schema.error import ErrorCode
from core.service.base import BaseService
from core.utils.exc.http import VancedHTTPException
from event.dto.attendance import AttendanceCreateDTO
from event.dto.attendance_change import (
    AttendanceChangedDTO,
    AttendanceChangeDTO,
    AttendanceDeclareDTO,
    ParticipationCountsDTO,
)
from event.dto.member_profile import ProfileViewerDTO
from event.exc.event import (
    AttendanceNotExistsException,
    MemberNotExistsException,
    ParticipationNotExistsException,
)
from event.service.attendance_stats import shown_attendance
from event.service.notification import notify_event_targets
from event.uow.attendance_change import AttendanceChangeUOW


def _forbidden(detail: ErrorCode) -> VancedHTTPException:
    return VancedHTTPException(status_code=403, detail=detail)


class AttendanceChangeService(BaseService[AttendanceChangeUOW]):
    async def change(
        self,
        attendance_id: UUID,
        change: AttendanceChangeDTO,
        viewer: ProfileViewerDTO,
    ) -> AttendanceChangedDTO:
        """The leader of the collective (and a superuser) may set anything; the member
        whose place it is may mark it and comment on it until it is verified."""
        async with self.uow as uow:
            owner = await uow.attendances.ownership(attendance_id)
            if owner is None:
                raise AttendanceNotExistsException()
            leads = viewer.is_superuser or (
                viewer.person_id is not None and owner.principal_id == viewer.person_id
            )
            if not leads:
                if (
                    viewer.person_id is None
                    or owner.member_person_id != viewer.person_id
                ):
                    raise _forbidden(ErrorCode.NOT_MEMBER_PERSON)
                if "is_verified" in change.fields_set:
                    raise _forbidden(ErrorCode.NOT_COLLECTIVE_PRINCIPAL)
                if owner.is_verified:
                    raise _forbidden(ErrorCode.ATTENDANCE_ALREADY_VERIFIED)
            data = dto_dict(change, only_set=True)
            if data:
                attendance = await uow.attendances.update_one(attendance_id, data)
            else:
                attendance = await uow.attendances.get_by_id(attendance_id)
            if attendance is None:
                raise AttendanceNotExistsException()
            result = shown_attendance(attendance)
            counts = await uow.view.attendance_counts([owner.participation_id])
            found = counts.get(owner.participation_id)
            attended, total = (found.attended, found.total) if found else (0, 0)
            await uow.commit()
        return AttendanceChangedDTO(
            attendance=result,
            participation=ParticipationCountsDTO(
                id=owner.participation_id,
                event_id=owner.event_id,
                collective_id=owner.collective_id,
                attended_count=attended,
                total_count=total,
            ),
        )

    async def declare(
        self, data: AttendanceDeclareDTO, viewer: ProfileViewerDTO
    ) -> AttendanceChangedDTO:
        """Declares a member for the event: the place nobody has marked yet. Only the
        leader of the collective (and a superuser) may; a place that is already
        there is returned as it is."""
        async with self.uow as uow:
            owner = await uow.attendances.participation_owner(data.participation_id)
            if owner is None:
                raise ParticipationNotExistsException()
            if not (
                viewer.is_superuser
                or (
                    viewer.person_id is not None
                    and owner.principal_id == viewer.person_id
                )
            ):
                raise _forbidden(ErrorCode.NOT_COLLECTIVE_PRINCIPAL)
            members = await uow.view.members_by_ids([data.member_id])
            if not members or members[0].collective_id != owner.collective_id:
                raise MemberNotExistsException()
            existing = await uow.view.attendances_of_members(
                [data.participation_id], [data.member_id]
            )
            found = existing[0] if existing else None
            created = found is None
            if found is None:
                found = await uow.attendances.add_n_return(
                    data=dto_dict(
                        AttendanceCreateDTO(
                            member_id=data.member_id,
                            participation_id=data.participation_id,
                        )
                    )
                )
                await uow.attendances.session.flush(objects=[found])
            result = shown_attendance(found)
            counts = await uow.view.attendance_counts([data.participation_id])
            counted = counts.get(data.participation_id)
            attended, total = (counted.attended, counted.total) if counted else (0, 0)
            await uow.commit()
            if created:
                await notify_event_targets(uow, attendance_ids=[result.id])
        return AttendanceChangedDTO(
            attendance=result,
            participation=ParticipationCountsDTO(
                id=data.participation_id,
                event_id=owner.event_id,
                collective_id=owner.collective_id,
                attended_count=attended,
                total_count=total,
            ),
        )
