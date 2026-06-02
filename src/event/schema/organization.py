from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import TYPE_CHECKING

from core.utils.mixin.pydantic import PatchModel

if TYPE_CHECKING:
    from .event import EventRead


class OrganizationCreate(BaseModel):
    name: str
    description: str | None = None
    type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationRead(OrganizationCreate):
    id: UUID
    events: list["EventRead"] = []


class OrganizationPatchData(PatchModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationPatch(OrganizationPatchData):
    id: UUID


class OrganizationPutData(OrganizationCreate): ...


class OrganizationPut(OrganizationPutData):
    id: UUID