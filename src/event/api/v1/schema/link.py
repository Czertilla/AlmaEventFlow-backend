from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1
from event.dto.link import LinkCreateDTO, LinkPatchDTO, LinkPutDTO
from event.enum.link import EventLinkTypeEnumV1


class LinkCreateData(BaseModel):
    url: str
    type: EventLinkTypeEnumV1
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LinkCreate(LinkCreateData, ToDTOMixinV1):
    __dto_cls__ = LinkCreateDTO

    event_id: UUID


class LinkRead(FromDTOMixinV1, LinkCreate, UUIDMixinV1, TimestampMixinV1): ...


class LinkPatchData(PatchModelV1):
    url: str | None = None
    type: EventLinkTypeEnumV1 | None = None
    description: str | None = None


class LinkPatch(LinkPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = LinkPatchDTO


class LinkPutData(LinkCreateData): ...


class LinkPut(LinkPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = LinkPutDTO
