from uuid import UUID
from pydantic import BaseModel, ConfigDict

from core.utils.mixin.pydantic import PatchModel, UUIDMixin
from event.enum.link import EventLinkType


class LinkCreateData(BaseModel):
    url: str
    type: EventLinkType
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LinkCreate(LinkCreateData):
    event_id: UUID


class LinkRead(LinkCreate, UUIDMixin): ...


class LinkPatchData(PatchModel):
    url: str | None = None
    type: str | None = None
    description: str | None = None


class LinkPatch(LinkPatchData, UUIDMixin): ...


class LinkPutData(LinkCreateData): ...


class LinkPut(LinkPutData, UUIDMixin): ...
