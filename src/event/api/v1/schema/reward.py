from uuid import UUID

from fastapi import UploadFile
from pydantic import BaseModel, ConfigDict, HttpUrl

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1
from event.dto.reward import RewardCreateDTO, RewardPatchDTO, RewardPutDTO


class RewardCreateData(BaseModel):
    name: str
    degree: int | None = None

    model_config = ConfigDict(from_attributes=True)


class RewardCreate(RewardCreateData, ToDTOMixinV1):
    __dto_cls__ = RewardCreateDTO

    participation_id: UUID
    file: UploadFile | None = None


class RewardRead(FromDTOMixinV1, RewardCreateData, UUIDMixinV1, TimestampMixinV1):
    participation_id: UUID | None
    file_link: HttpUrl | None = None


class RewardPatchData(PatchModelV1):
    name: str | None = None
    file: UploadFile | None = None
    degree: int | None = None

    model_config = ConfigDict(from_attributes=True)


class RewardPatch(RewardPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = RewardPatchDTO


class RewardPutData(RewardCreateData): ...


class RewardPut(RewardPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = RewardPutDTO
