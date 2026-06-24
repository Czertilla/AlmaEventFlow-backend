from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.enum.notify import TransportTypeEnum


class ClientCreate(BaseModel):
    transport: TransportTypeEnum = TransportTypeEnum.webpush
    endpoint: str = Field(max_length=512)
    label: str | None = Field(default=None, max_length=256)
    payload: dict[str, str] = Field(
        default_factory=dict,
        description="Transport-specific data. Web-push: p256dh, auth.",
    )


class ClientRead(BaseModel):
    id: UUID
    transport: TransportTypeEnum
    endpoint: str
    label: str | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientTarget(BaseModel):
    """Internal delivery view of a client, including ``payload``. Passed to
    transports; never exposed over HTTP (unlike ``ClientRead``)."""

    id: UUID
    transport: TransportTypeEnum
    endpoint: str
    payload: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)
