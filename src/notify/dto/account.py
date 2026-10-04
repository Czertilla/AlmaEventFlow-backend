from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccountDTO:
    id: UUID
    email: str
    is_verified: bool = False
    locale: str | None = None
