from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.utils.mixin.pydantic import PatchModel, TimestampMixin, UUIDMixin


class CollectiveCreate(BaseModel):
    id: UUID
    principal_id: UUID
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class CollectiveRead(CollectiveCreate, TimestampMixin, UUIDMixin): ...


class MyCollectiveRead(BaseModel):
    """Summary used by ``GET /me/collectives`` (and the bot's collective
    lookups) -- just enough to let a caller pick one of their own led
    collectives by name."""

    id: UUID
    name: str
    principal_id: UUID
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class CollectivePatchData(PatchModel):
    id: UUID | None = None
    principal_id: UUID | None = None
    is_verified: bool | None = None


class CollectivePatch(CollectivePatchData, UUIDMixin): ...


class CollectivePutData(CollectiveCreate): ...


class CollectivePut(CollectivePutData, UUIDMixin): ...
