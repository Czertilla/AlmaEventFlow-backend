from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1


class CollectiveCreate(BaseModel):
    id: UUID
    principal_id: UUID
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class CollectiveRead(CollectiveCreate, TimestampMixinV1, UUIDMixinV1): ...


class MyCollectiveRead(FromDTOMixinV1, BaseModel):
    """Summary used by ``GET /me/collectives`` (and the bot's collective
    lookups) -- just enough to let a caller pick one of their own led
    collectives by name."""

    id: UUID
    name: str
    principal_id: UUID
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class CollectivePatchData(PatchModelV1):
    id: UUID | None = None
    principal_id: UUID | None = None
    is_verified: bool | None = None


class CollectivePatch(CollectivePatchData, UUIDMixinV1): ...


class CollectivePutData(CollectiveCreate): ...


class CollectivePut(CollectivePutData, UUIDMixinV1): ...
