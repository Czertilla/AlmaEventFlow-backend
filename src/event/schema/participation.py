from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from core.utils.mixin.pydantic import PatchModel, UUIDMixin

from event.enum.priority import Priority


class ParticipationCreateData(BaseModel):
    event_id: UUID
    priority_degree: Priority | None = Field(alias="priority", default=None)

    model_config = ConfigDict(from_attributes=True)


class ParticipationCreate(ParticipationCreateData):
    collective_id: UUID


class ParticipationRead(ParticipationCreate, UUIDMixin): ...


class ParticipationPatchData(PatchModel):
    event_id: UUID | None = None
    priority_degree: Priority | None = Field(alias="priority", default=None)

    model_config = ConfigDict(from_attributes=True)


class ParticipationPatch(ParticipationPatchData, UUIDMixin): ...


class ParticipationPutData(ParticipationCreateData): ...


class ParticipationPut(ParticipationPutData, UUIDMixin): ...
