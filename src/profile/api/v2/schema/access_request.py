from datetime import datetime
from profile.api.v2.schema.access_log import AccessFieldRead
from profile.dto.access_request import AccessExportCreateDTO, AccessRequestCreateDTO
from profile.enum.access import GrantState, SkipReason
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class AccessRequestCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = AccessRequestCreateDTO

    collective_id: UUID
    fields: list[str] = Field(
        min_length=1,
        max_length=64,
        description="Keys of grantable fields (`GET /access-requests/fields`).",
    )
    comment: str = Field(
        max_length=4000,
        description="Why the data is needed. Shown to every member as written; "
        "its length after trimming is bounded by the server settings.",
    )
    expires_at: AwareDatetime = Field(
        description="When the grants of this request stop opening the data."
    )


class GrantStateRead(FromDTOMixinV1, BaseModel):
    person_id: UUID
    status: GrantState

    model_config = ConfigDict(from_attributes=True)


class AccessRequestRead(FromDTOMixinV1, BaseModel):
    id: UUID
    collective_id: UUID
    collective_name: str
    fields: list[AccessFieldRead]
    comment: str
    expires_at: datetime
    created_at: datetime
    is_expired: bool
    grants: list[GrantStateRead] = Field(
        description="One per member asked: who and how they answered, no data."
    )

    model_config = ConfigDict(from_attributes=True)


class IncomingGrantRead(FromDTOMixinV1, BaseModel):
    id: UUID
    status: GrantState
    created_at: datetime
    decided_at: datetime | None
    revoked_at: datetime | None
    request_id: UUID
    grantee_person_id: UUID
    grantee_name: str | None
    collective_id: UUID
    collective_name: str
    fields: list[AccessFieldRead]
    comment: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccessExportCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = AccessExportCreateDTO

    fields: list[str] | None = Field(
        default=None,
        max_length=64,
        description="Fields of the request to export; all of them when omitted.",
    )


class ExportedSubjectRead(FromDTOMixinV1, BaseModel):
    person_id: UUID
    records: list[dict[str, Any]] = Field(
        description="One record per stored row (a passport with its name variant, "
        "a contact, the person's profile): field key to value, a field of several "
        "columns as an object of them."
    )

    model_config = ConfigDict(from_attributes=True)


class SkippedSubjectRead(FromDTOMixinV1, BaseModel):
    person_id: UUID
    status: SkipReason

    model_config = ConfigDict(from_attributes=True)


class AccessExportRead(FromDTOMixinV1, BaseModel):
    request_id: UUID
    exported_at: datetime
    fields: list[AccessFieldRead]
    subjects: list[ExportedSubjectRead]
    skipped: list[SkippedSubjectRead]

    model_config = ConfigDict(from_attributes=True)
