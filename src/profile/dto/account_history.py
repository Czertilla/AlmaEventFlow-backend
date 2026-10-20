from dataclasses import dataclass
from datetime import datetime
from profile.enum.account import PersonLinkAction
from uuid import UUID

from core.enum.profile import PersonLinkSource


@dataclass(frozen=True, slots=True)
class AccountLinkChangeDTO:
    id: UUID
    user_id: UUID
    old_person_id: UUID | None
    new_person_id: UUID | None
    action: PersonLinkAction
    source: PersonLinkSource
    actor_id: UUID | None
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AccountLinkChangeFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
    user_id: UUID | None = None
    person_id: UUID | None = None
    actor_id: UUID | None = None
    action: PersonLinkAction | None = None
    source: PersonLinkSource | None = None
    created_at__gte: datetime | None = None
    created_at__lte: datetime | None = None
