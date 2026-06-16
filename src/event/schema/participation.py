from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from core.utils.mixin.pydantic import PatchModel, UUIDMixin

from event.enum.priority import EventPriorityEnumV1


class ParticipationCreateData(BaseModel):
    event_id: UUID
    priority_degree: EventPriorityEnumV1 | None = Field(
        alias="EventPriorityEnumV1", default=None
    )

    model_config = ConfigDict(from_attributes=True)


class ParticipationCreate(ParticipationCreateData):
    collective_id: UUID


class ParticipationRead(ParticipationCreate, UUIDMixin): ...


class ParticipationPatchData(PatchModel):
    event_id: UUID | None = None
    priority_degree: EventPriorityEnumV1 | None = Field(
        alias="EventPriorityEnumV1", default=None
    )

    model_config = ConfigDict(from_attributes=True)


class ParticipationPatch(ParticipationPatchData, UUIDMixin): ...


class ParticipationPutData(ParticipationCreateData): ...


class ParticipationPut(ParticipationPutData, UUIDMixin): ...
