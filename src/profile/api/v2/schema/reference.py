from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1


class ReferenceName(BaseModel):
    name: str = Field(min_length=1, max_length=128)

    model_config = ConfigDict(str_strip_whitespace=True)


class DietReference(ReferenceName):
    name: str = Field(min_length=1, max_length=128)


class DegreeReference(ReferenceName):
    name: str = Field(min_length=1, max_length=32)


class FacultyReference(ReferenceName):
    university_id: UUID


class StudentGroupReference(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    degree_id: int
    faculty_id: UUID
    grade: int = Field(ge=1, le=12)

    model_config = ConfigDict(str_strip_whitespace=True)


class OrganizationRefRead(FromDTOMixinV1, BaseModel):
    id: UUID
    name: str
    type: str

    model_config = ConfigDict(from_attributes=True)
