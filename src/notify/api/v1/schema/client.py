from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.enum.notify import TransportTypeEnum
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from notify.dto.client import ClientCreateDTO


class ClientCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = ClientCreateDTO

    transport: TransportTypeEnum = TransportTypeEnum.webpush
    endpoint: str = Field(max_length=512)
    label: str | None = Field(default=None, max_length=256)
    payload: dict[str, str] = Field(
        default_factory=dict,
        description="Transport-specific data. Web-push: p256dh, auth.",
    )


class ClientRead(FromDTOMixinV1, BaseModel):
    id: UUID
    transport: TransportTypeEnum
    endpoint: str
    label: str | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
