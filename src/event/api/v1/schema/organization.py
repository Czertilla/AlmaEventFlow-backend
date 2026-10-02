from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.model import PatchModelV1
from event.api.v1.schema.event import EventRead


class OrganizationCreate(BaseModel):
    name: str
    description: str | None = None
    type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationRead(OrganizationCreate):
    id: UUID
    events: list[EventRead] = []


class OrganizationPatchData(PatchModelV1):
    name: str | None = None
    description: str | None = None
    type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationPatch(OrganizationPatchData):
    id: UUID


class OrganizationPutData(OrganizationCreate): ...


class OrganizationPut(OrganizationPutData):
    id: UUID
