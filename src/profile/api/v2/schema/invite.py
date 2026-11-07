from profile.dto.invite import InviteTokenCreateDTO
from uuid import UUID

from pydantic import BaseModel, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1


class InviteTokenData(BaseModel):
    expires_in: int | None = Field(
        default=None, gt=0, description="Seconds the invitation stays valid."
    )


class InviteTokenCreate(InviteTokenData, ToDTOMixinV1):
    __dto_cls__ = InviteTokenCreateDTO

    person_id: UUID


class InviteTokenRead(FromDTOMixinV1, BaseModel):
    token: str
    expires_at: int


class InvitePreviewData(BaseModel):
    token: str = Field(min_length=1, max_length=4096)


class InvitePreviewRead(FromDTOMixinV1, BaseModel):
    surname: str
    name: str
    patronymic: str | None
