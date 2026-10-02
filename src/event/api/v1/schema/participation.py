from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1
from event.dto.participation import (
    ParticipationCreateDTO,
    ParticipationPatchDTO,
    ParticipationPutDTO,
)
from event.enum.priority import EventPriorityEnumV1


class ParticipationCreateData(BaseModel):
    event_id: UUID
    priority_degree: EventPriorityEnumV1 | None = Field(
        alias="EventPriorityEnumV1", default=None
    )

    model_config = ConfigDict(from_attributes=True)


class ParticipationCreate(ParticipationCreateData, ToDTOMixinV1):
    __dto_cls__ = ParticipationCreateDTO

    collective_id: UUID


class ParticipationRead(FromDTOMixinV1, ParticipationCreate, UUIDMixinV1):
    collective_name: str | None = None


class ParticipationPatchData(PatchModelV1):
    event_id: UUID | None = None
    priority_degree: EventPriorityEnumV1 | None = Field(
        alias="EventPriorityEnumV1", default=None
    )

    model_config = ConfigDict(from_attributes=True)


class ParticipationPatch(ParticipationPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = ParticipationPatchDTO


class ParticipationPutData(ParticipationCreateData): ...


class ParticipationPut(ParticipationPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = ParticipationPutDTO
