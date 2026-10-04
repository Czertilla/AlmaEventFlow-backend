from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionDTO:
    id: UUID
    device_info: str | None
    ip_address: str | None
    created_at: datetime
    last_used_at: datetime
    is_current: bool = False


@dataclass(frozen=True, slots=True)
class SessionTokenDTO:
    user_id: UUID
    session_id: UUID
    refresh_token: str
