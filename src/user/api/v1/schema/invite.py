import uuid

from pydantic import BaseModel

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from user.dto.invite import InviteTokenCreateDTO


class InviteTokenCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = InviteTokenCreateDTO

    person_id: uuid.UUID
    expires_in: int | None = None


class InviteTokenRead(FromDTOMixinV1, BaseModel):
    token: str
    expires_at: int
