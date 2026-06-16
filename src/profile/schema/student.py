from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from core.utils.mixin.pydantic import IDMixin, PatchModel, UUIDMixin

from profile.schema.person import PersonRead
from profile.schema.profile import ProfileRead


class StudentDegreeCreate(BaseModel):
    name: str = Field(max_length=32)

    model_config = ConfigDict(from_attributes=True)


class StudentDegreeRead(StudentDegreeCreate, IDMixin): ...


class StudentDegreePatchData(PatchModel):
    name: str | None = Field(max_length=32, default=None)


class StudentDegreePatch(StudentDegreePatchData, IDMixin): ...


class StudentDegreePutData(StudentDegreeCreate): ...


class StudentDegreePut(StudentDegreePutData, IDMixin): ...


class StudentGroupCreate(BaseModel):
    name: str = Field(max_length=32)
    degree_id: int
    faculty_id: UUID
    grade: int

    model_config = ConfigDict(from_attributes=True)


class StudentGroupRead(StudentGroupCreate, IDMixin): ...


class StudentGroupPatchData(PatchModel):
    name: str | None = Field(max_length=32, default=None)
    degree_id: int | None = None
    faculty_id: UUID | None = None
    grade: int | None = None


class StudentGroupPatch(StudentGroupPatchData, IDMixin): ...


class StudentGroupPutData(StudentGroupCreate): ...


class StudentGroupPut(StudentGroupPutData, IDMixin): ...


class StudentCreate(BaseModel, UUIDMixin):
    student_id: str = Field(max_length=64)
    faculty_id: UUID | None = None
    group_id: int
    is_budget: bool | None = None
    is_full: bool | None = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class StudentRead(StudentCreate):
    person: PersonRead | None = None
    profile: ProfileRead | None = None
    group: StudentGroupRead | None = None


class StudentPatchData(PatchModel):
    student_id: str | None = Field(max_length=64, default=None)
    faculty_id: UUID | None = None
    group_id: int | None = None
    is_budget: bool | None = None
    is_full: bool | None = None
    is_active: bool | None = None


class StudentPatch(StudentPatchData, UUIDMixin): ...


class StudentPutData(StudentCreate): ...


class StudentPut(StudentPutData, UUIDMixin): ...
