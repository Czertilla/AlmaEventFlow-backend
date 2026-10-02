from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1


class CollectiveCreate(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None
    university_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectiveRead(CollectiveCreate, UUIDMixinV1):
    type: str = Field(default="collective", repr=False)


class CollectivePatchData(CollectiveCreate, PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)
    university_id: UUID | None = None


class CollectivePatch(CollectivePatchData, UUIDMixinV1): ...


class CollectivePutData(CollectiveCreate): ...


class CollectivePut(CollectivePutData, UUIDMixinV1): ...
