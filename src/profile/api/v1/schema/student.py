from profile.api.v1.schema.person import PersonRead
from profile.api.v1.schema.profile import ProfileRead
from profile.dto.student import (
    StudentCreateDTO,
    StudentDegreeCreateDTO,
    StudentDegreePatchDTO,
    StudentDegreePutDTO,
    StudentGroupCreateDTO,
    StudentGroupPatchDTO,
    StudentGroupPutDTO,
    StudentPatchDTO,
    StudentPutDTO,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import IDMixinV1, PatchModelV1, UUIDMixinV1


class StudentDegreeCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = StudentDegreeCreateDTO

    name: str = Field(max_length=32)

    model_config = ConfigDict(from_attributes=True)


class StudentDegreeRead(FromDTOMixinV1, StudentDegreeCreate, IDMixinV1): ...


class StudentDegreePatchData(PatchModelV1):
    name: str | None = Field(max_length=32, default=None)


class StudentDegreePatch(StudentDegreePatchData, IDMixinV1, ToDTOMixinV1):
    __dto_cls__ = StudentDegreePatchDTO


class StudentDegreePutData(StudentDegreeCreate): ...


class StudentDegreePut(StudentDegreePutData, IDMixinV1, ToDTOMixinV1):
    __dto_cls__ = StudentDegreePutDTO


class StudentGroupCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = StudentGroupCreateDTO

    name: str = Field(max_length=32)
    degree_id: int
    faculty_id: UUID
    grade: int

    model_config = ConfigDict(from_attributes=True)


class StudentGroupRead(FromDTOMixinV1, StudentGroupCreate, IDMixinV1): ...


class StudentGroupPatchData(PatchModelV1):
    name: str | None = Field(max_length=32, default=None)
    degree_id: int | None = None
    faculty_id: UUID | None = None
    grade: int | None = None


class StudentGroupPatch(StudentGroupPatchData, IDMixinV1, ToDTOMixinV1):
    __dto_cls__ = StudentGroupPatchDTO


class StudentGroupPutData(StudentGroupCreate): ...


class StudentGroupPut(StudentGroupPutData, IDMixinV1, ToDTOMixinV1):
    __dto_cls__ = StudentGroupPutDTO


class StudentBase(BaseModel, UUIDMixinV1):
    student_id: str = Field(max_length=64)
    faculty_id: UUID | None = None
    group_id: int
    is_budget: bool | None = None
    is_full: bool | None = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class StudentCreate(StudentBase, ToDTOMixinV1):
    __dto_cls__ = StudentCreateDTO


class StudentRead(FromDTOMixinV1, StudentBase):
    person: PersonRead | None = None
    profile: ProfileRead | None = None
    group: StudentGroupRead | None = None


class StudentPatchData(PatchModelV1):
    student_id: str | None = Field(max_length=64, default=None)
    faculty_id: UUID | None = None
    group_id: int | None = None
    is_budget: bool | None = None
    is_full: bool | None = None
    is_active: bool | None = None


class StudentPatch(StudentPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = StudentPatchDTO


class StudentPutData(StudentBase): ...


class StudentPut(StudentPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = StudentPutDTO
