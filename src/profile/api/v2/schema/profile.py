import datetime
from profile.api.v1.schema.contact import ContactItemRead
from profile.api.v1.schema.diet import DietRead
from profile.api.v1.schema.student import StudentGroupRead
from profile.dto.my_profile import (
    MyContactDTO,
    MyProfileWriteDTO,
    MyStudentDTO,
)
from profile.enum.contact import ContactType
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import TimestampMixinV1, UUIDMixinV1


class MyStudentData(BaseModel, ToDTOMixinV1):
    __dto_cls__ = MyStudentDTO

    student_id: str = Field(min_length=1, max_length=64)
    group_id: int
    faculty_id: UUID | None = None
    is_budget: bool | None = None
    is_full: bool | None = None
    is_active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)


class MyContactData(BaseModel, ToDTOMixinV1):
    __dto_cls__ = MyContactDTO

    id: UUID | None = Field(
        default=None,
        description="Keeps and changes an existing contact; one left out is deleted.",
    )
    type: ContactType
    value: str = Field(min_length=1, max_length=256)
    is_main: bool = False

    model_config = ConfigDict(str_strip_whitespace=True)


class MyProfileWrite(BaseModel, ToDTOMixinV1):
    __dto_cls__ = MyProfileWriteDTO

    surname: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    patronymic: str | None = Field(default=None, max_length=128)
    birthdate: datetime.date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None
    student: MyStudentData | None = Field(
        default=None, description="Left out or null: the user is not a student."
    )
    contacts: list[MyContactData] = Field(default_factory=list, max_length=50)

    model_config = ConfigDict(str_strip_whitespace=True)


class MyStudentRead(FromDTOMixinV1, BaseModel):
    student_id: str
    group_id: int
    faculty_id: UUID | None
    is_budget: bool | None
    is_full: bool | None
    is_active: bool
    group: StudentGroupRead | None

    model_config = ConfigDict(from_attributes=True)


class MyProfileRead(FromDTOMixinV1, BaseModel, UUIDMixinV1, TimestampMixinV1):
    surname: str
    name: str
    patronymic: str | None
    birthdate: datetime.date | None
    workplace_id: UUID | None
    diet_id: int | None
    diet: DietRead | None
    student: MyStudentRead | None
    contacts: list[ContactItemRead]

    model_config = ConfigDict(from_attributes=True)
