from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from core.schema.message.core import MQEvent, MQRequest


class OrganizationData(MQRequest):
    id: UUID
    name: str = Field(max_length=128)
    type: str = Field(max_length=16)
    principal_id: UUID | None = None

    model_config = ConfigDict(extra="ignore")


class OrganizationCreatedEvent(MQEvent[OrganizationData]): ...


class OrganizationUpdatedEvent(OrganizationCreatedEvent): ...


class OrganizationDelete(MQRequest):
    id: UUID


class OrganizationDeletedEvent(MQEvent[OrganizationDelete]): ...
