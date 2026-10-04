from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class InviteTokenCreateDTO:
    person_id: UUID
    expires_in: int | None = None


@dataclass(frozen=True, slots=True)
class InviteTokenDTO:
    token: str
    expires_at: int
