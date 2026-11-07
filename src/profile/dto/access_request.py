from dataclasses import dataclass
from datetime import datetime
from profile.dto.access import AccessFieldDTO
from profile.enum.access import GrantState, SkipReason
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CollectiveLeadDTO:
    is_principal: bool
    name: str | None = None
    is_verified: bool = False


@dataclass(frozen=True, slots=True)
class AccessRequestCreateDTO:
    collective_id: UUID
    fields: list[str]
    comment: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class GrantStateDTO:
    person_id: UUID
    status: GrantState


@dataclass(frozen=True, slots=True)
class AccessRequestDTO:
    id: UUID
    collective_id: UUID
    collective_name: str
    fields: list[AccessFieldDTO]
    comment: str
    expires_at: datetime
    created_at: datetime
    is_expired: bool
    grants: list[GrantStateDTO]


@dataclass(frozen=True, slots=True)
class IncomingGrantDTO:
    id: UUID
    status: GrantState
    created_at: datetime
    decided_at: datetime | None
    revoked_at: datetime | None
    request_id: UUID
    grantee_person_id: UUID
    grantee_name: str | None
    collective_id: UUID
    collective_name: str
    fields: list[AccessFieldDTO]
    comment: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class AccessExportCreateDTO:
    fields: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ExportedSubjectDTO:
    person_id: UUID
    records: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class SkippedSubjectDTO:
    person_id: UUID
    status: SkipReason


@dataclass(frozen=True, slots=True)
class AccessExportDTO:
    request_id: UUID
    exported_at: datetime
    fields: list[AccessFieldDTO]
    subjects: list[ExportedSubjectDTO]
    skipped: list[SkippedSubjectDTO]
