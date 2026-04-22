from uuid import UUID
from pydantic import BaseModel, ConfigDict, HttpUrl
from fastapi import UploadFile

from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class RewardCreateData(BaseModel):
    name: str
    degree: int | None = None

    model_config = ConfigDict(from_attributes=True)


class RewardCreate(RewardCreateData):
    participation_id: UUID
    file: UploadFile | None = None


class RewardRead(RewardCreateData, UUIDMixin):
    participation_id: UUID
    file_link: HttpUrl | None = None


class RewardPatchData(PatchModel):
    name: str | None = None
    file: UploadFile | None = None
    degree: int | None = None

    model_config = ConfigDict(from_attributes=True)


class RewardPatch(RewardPatchData, UUIDMixin): ...


class RewardPutData(RewardCreateData): ...


class RewardPut(RewardPutData, UUIDMixin): ...
