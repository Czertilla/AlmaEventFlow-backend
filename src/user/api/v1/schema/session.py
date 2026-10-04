import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1


class SessionRead(FromDTOMixinV1, BaseModel):
    """A single authenticated session of the current user, as surfaced by the
    self-service session manager. ``is_current`` marks the session bound to the
    refresh token presented in the request."""

    id: uuid.UUID
    device_info: str | None
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)
