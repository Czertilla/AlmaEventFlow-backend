from uuid import UUID
from pydantic import BaseModel, ConfigDict

from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class RoleCreateData(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(RoleCreateData):
    collective_id: UUID


class RolePreview(RoleCreateData, UUIDMixin):
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class RoleRead(RoleCreate, UUIDMixin): ...


class RolePatchData(PatchModel):
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RolePatch(RolePatchData, UUIDMixin): ...


class RolePutData(RoleCreateData): ...


class RolePut(RolePutData, UUIDMixin): ...
