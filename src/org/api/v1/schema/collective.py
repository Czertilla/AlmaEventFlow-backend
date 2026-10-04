from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1
from org.dto.collective import (
    CollectiveCreateDTO,
    CollectivePatchDTO,
    CollectivePutDTO,
)


class CollectiveBase(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None
    university_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectiveCreate(CollectiveBase, ToDTOMixinV1):
    __dto_cls__ = CollectiveCreateDTO


class CollectiveRead(FromDTOMixinV1, CollectiveBase, UUIDMixinV1, TimestampMixinV1):
    type: str = Field(default="collective", repr=False)


class CollectivePatchData(CollectiveBase, PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)
    university_id: UUID | None = None


class CollectivePatch(CollectivePatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = CollectivePatchDTO


class CollectivePutData(CollectiveBase): ...


class CollectivePut(CollectivePutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = CollectivePutDTO
