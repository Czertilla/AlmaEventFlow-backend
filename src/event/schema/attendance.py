from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from core.utils.mixin.pydantic import PatchModel, TimestampMixin, UUIDMixin


class AttendanceCreate(BaseModel):
    member_id: UUID
    participation_id: UUID
    is_attended: bool | None = False
    comment: str | None = Field(max_length=512, default=None)

    model_config = ConfigDict(from_attributes=True)


class AttendanceRead(AttendanceCreate, TimestampMixin, UUIDMixin): ...


class AttendancePatchData(PatchModel):
    is_attended: bool | None = None
    comment: str | None = Field(max_length=512, default=None)


class AttendancePatch(AttendancePatchData, UUIDMixin): ...


class AttendancePutData(AttendanceCreate): ...


class AttendancePut(AttendancePutData, UUIDMixin): ...
