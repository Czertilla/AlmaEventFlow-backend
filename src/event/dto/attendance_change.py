from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin
from event.dto.attendance import AttendanceViewDTO


@dataclass(frozen=True, slots=True, kw_only=True)
class AttendanceChangeDTO(FieldsSetDTOMixin):
    is_attended: bool = False
    is_verified: bool | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class AttendanceDeclareDTO:
    participation_id: UUID
    member_id: UUID


@dataclass(frozen=True, slots=True)
class ParticipationCountsDTO:
    id: UUID
    event_id: UUID
    collective_id: UUID
    attended_count: int
    total_count: int


@dataclass(frozen=True, slots=True)
class AttendanceChangedDTO:
    attendance: AttendanceViewDTO
    participation: ParticipationCountsDTO
