import datetime
from dataclasses import dataclass, field
from profile.dto.contact import ContactDTO
from profile.dto.diet import DietDTO
from profile.dto.student import StudentGroupDTO
from profile.enum.contact import ContactType
from uuid import UUID


@dataclass(frozen=True, slots=True)
class MyStudentDTO:
    student_id: str
    group_id: int
    faculty_id: UUID | None = None
    is_budget: bool | None = None
    is_full: bool | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class MyContactDTO:
    type: ContactType
    value: str
    is_main: bool = False
    id: UUID | None = None


@dataclass(frozen=True, slots=True)
class MyProfileWriteDTO:
    surname: str
    name: str
    patronymic: str | None = None
    birthdate: datetime.date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None
    student: MyStudentDTO | None = None
    contacts: list[MyContactDTO] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MyStudentReadDTO:
    student_id: str
    group_id: int
    faculty_id: UUID | None
    is_budget: bool | None
    is_full: bool | None
    is_active: bool
    group: StudentGroupDTO | None


@dataclass(frozen=True, slots=True)
class MyProfileDTO:
    id: UUID
    surname: str
    name: str
    patronymic: str | None
    birthdate: datetime.date | None
    workplace_id: UUID | None
    diet_id: int | None
    diet: DietDTO | None
    student: MyStudentReadDTO | None
    contacts: list[ContactDTO]
    created_at: datetime.datetime
    edited_at: datetime.datetime | None
