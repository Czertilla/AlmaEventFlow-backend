from uuid import UUID

from pydantic import ConfigDict, Field

from core.schema.message.core import MQEvent, MQRequest


class OrganizationData(MQRequest):
    id: UUID
    name: str = Field(max_length=128)
    type: str = Field(max_length=16)
    principal_id: UUID | None = None

    model_config = ConfigDict(extra="ignore")


class OrganizationRef(MQRequest):
    id: UUID
    name: str = Field(max_length=128)
    type: str = Field(max_length=16)


class ResolveUniversityRequest(MQRequest):
    name: str = Field(min_length=1, max_length=128)


class ResolveFacultyRequest(MQRequest):
    name: str = Field(min_length=1, max_length=128)
    university_id: UUID


class ResolveOrganizationRequest(MQRequest):
    name: str = Field(min_length=1, max_length=128)


class GetOrganizationRequest(MQRequest):
    id: UUID


class OrganizationCreatedEvent(MQEvent[OrganizationData]): ...


class OrganizationUpdatedEvent(OrganizationCreatedEvent): ...


class OrganizationDelete(MQRequest):
    id: UUID


class OrganizationDeletedEvent(MQEvent[OrganizationDelete]): ...
