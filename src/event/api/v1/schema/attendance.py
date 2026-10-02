from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import (
    PatchModelV1,
    TimestampMixinV1,
    UUIDMixinV1,
)
from event.dto.attendance import (
    AttendanceCreateDTO,
    AttendanceMinePatchDTO,
    AttendancePatchDTO,
    AttendancePutDTO,
)


class AttendanceCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = AttendanceCreateDTO

    member_id: UUID
    participation_id: UUID
    is_attended: bool | None = False
    is_verified: bool | None = False
    comment: str | None = Field(max_length=512, default=None)

    model_config = ConfigDict(from_attributes=True)


class AttendanceRead(
    FromDTOMixinV1, AttendanceCreate, TimestampMixinV1, UUIDMixinV1
): ...


class AttendancePatchData(PatchModelV1, ToDTOMixinV1):
    __dto_cls__ = AttendanceMinePatchDTO

    is_attended: bool | None = None
    comment: str | None = Field(max_length=512, default=None)


class AttendancePrincipalPatchData(AttendancePatchData):
    is_verified: bool | None = None


class AttendancePatch(AttendancePrincipalPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = AttendancePatchDTO


class AttendancePutData(AttendanceCreate): ...


class AttendancePut(AttendancePutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = AttendancePutDTO
