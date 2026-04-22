from pydantic import BaseModel, ConfigDict
from typing import TYPE_CHECKING, Optional

from core.utils.mixin.pydantic import PatchModel, UUIDMixin

if TYPE_CHECKING:
    from .event import EventRead


class OrganizationCreate(BaseModel):
    name: str
    description: str | None = None
    type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationRead(OrganizationCreate):
    id: int
    events: list["EventRead"] = []


class OrganizationPatchData(PatchModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationPatch(OrganizationPatchData):
    id: int


class OrganizationPutData(OrganizationCreate): ...


class OrganizationPut(OrganizationPutData):
    id: int