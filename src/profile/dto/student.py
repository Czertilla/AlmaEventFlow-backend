from dataclasses import dataclass
from profile.dto.person import PersonDTO
from profile.dto.profile import ProfileDTO
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin


@dataclass(frozen=True, slots=True)
class StudentDegreeCreateDTO:
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class StudentDegreePatchDTO(FieldsSetDTOMixin):
    id: int
    name: str | None = None


@dataclass(frozen=True, slots=True)
class StudentDegreePutDTO:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class StudentDegreeDTO:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class StudentDegreeFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None


@dataclass(frozen=True, slots=True)
class StudentGroupCreateDTO:
    name: str
    degree_id: int
    faculty_id: UUID
    grade: int


@dataclass(frozen=True, slots=True, kw_only=True)
class StudentGroupPatchDTO(FieldsSetDTOMixin):
    id: int
    name: str | None = None
    degree_id: int | None = None
    faculty_id: UUID | None = None
    grade: int | None = None


@dataclass(frozen=True, slots=True)
class StudentGroupPutDTO:
    id: int
    name: str
    degree_id: int
    faculty_id: UUID
    grade: int


@dataclass(frozen=True, slots=True)
class StudentGroupDTO:
    id: int
    name: str
    degree_id: int
    faculty_id: UUID
    grade: int


@dataclass(frozen=True, slots=True)
class StudentGroupFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
    degree_id: int | None = None
    faculty_id: UUID | None = None
    grade: int | None = None


@dataclass(frozen=True, slots=True)
class StudentCreateDTO:
    id: UUID
    student_id: str
    group_id: int
    faculty_id: UUID | None = None
    is_budget: bool | None = None
    is_full: bool | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class StudentPatchDTO(FieldsSetDTOMixin):
    id: UUID
    student_id: str | None = None
    faculty_id: UUID | None = None
    group_id: int | None = None
    is_budget: bool | None = None
    is_full: bool | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class StudentPutDTO:
    id: UUID
    student_id: str
    group_id: int
    faculty_id: UUID | None = None
    is_budget: bool | None = None
    is_full: bool | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class StudentDTO:
    id: UUID
    student_id: str
    faculty_id: UUID | None
    group_id: int
    is_budget: bool | None
    is_full: bool | None
    is_active: bool
    person: PersonDTO | None
    profile: ProfileDTO | None
    group: StudentGroupDTO | None


@dataclass(frozen=True, slots=True)
class StudentFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
    group_id: int | None = None
    faculty_id: UUID | None = None
    is_active: bool | None = None
