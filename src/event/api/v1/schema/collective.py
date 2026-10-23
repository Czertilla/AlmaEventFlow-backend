from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1
from event.dto.collective import CollectivePatchDTO


class EventCollectiveRead(FromDTOMixinV1, BaseModel):
    """What the event service knows of a collective: the confirmation is its own."""

    id: UUID
    name: str
    principal_id: UUID | None
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class MyCollectiveRead(FromDTOMixinV1, BaseModel):
    """Summary used by ``GET /me/collectives`` (and the bot's collective
    lookups) -- just enough to let a caller pick one of their own led
    collectives by name."""

    id: UUID
    name: str
    principal_id: UUID
    is_verified: bool

    model_config = ConfigDict(from_attributes=True)


class EventCollectivePatchData(PatchModelV1):
    is_verified: bool | None = None


class EventCollectivePatch(EventCollectivePatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = CollectivePatchDTO
