from dataclasses import dataclass
from datetime import datetime
from profile.dto.access import AccessFieldDTO
from uuid import UUID


@dataclass(frozen=True, slots=True)
class KeyStatusDTO:
    by_key_ref: dict[str, int]
    by_dek_version: dict[int, int]
    destroyed: int


@dataclass(frozen=True, slots=True)
class RewrapReportDTO:
    target: str
    found: int
    rewrapped: int
    dry_run: bool


@dataclass(frozen=True, slots=True)
class RotationReportDTO:
    found: int
    rotated: int
    dry_run: bool


@dataclass(frozen=True, slots=True)
class DestroyKeyDTO:
    confirm_person_id: UUID
    reason: str


@dataclass(frozen=True, slots=True)
class DestroyedKeyDTO:
    person_id: UUID
    destroyed_at: datetime
    fields: list[AccessFieldDTO]
    rows_deleted: int
    rows_cleared: int
