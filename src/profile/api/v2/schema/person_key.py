from datetime import datetime
from profile.api.v2.schema.access_log import AccessFieldRead
from profile.dto.key_maintenance import DestroyKeyDTO
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class DestroyKeyData(BaseModel, ToDTOMixinV1):
    __dto_cls__ = DestroyKeyDTO

    confirm_person_id: UUID = Field(
        description="The id of the person once more: a mistyped path destroys nothing."
    )
    reason: str = Field(
        min_length=10,
        max_length=500,
        description="Why; told to the person with the notice.",
    )


class DestroyedKeyRead(FromDTOMixinV1, BaseModel):
    person_id: UUID
    destroyed_at: datetime
    fields: list[AccessFieldRead] = Field(description="The encrypted fields destroyed.")
    rows_deleted: int
    rows_cleared: int

    model_config = ConfigDict(from_attributes=True)
