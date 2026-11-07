from dataclasses import dataclass
from datetime import datetime
from profile.enum.access import AccessAction
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ViewerDTO:
    """Who reads personal data: the account, the person it is linked to in
    `profile` (none for an unlinked account) and the HTTP request it came with."""

    user_id: UUID
    person_id: UUID | None
    is_superuser: bool
    http_request_id: str | None = None

    def is_subject(self, person_id: UUID) -> bool:
        return self.person_id == person_id


@dataclass(frozen=True, slots=True)
class AccessFieldDTO:
    key: str
    label: str


@dataclass(frozen=True, slots=True)
class AccessLogEntryDTO:
    id: UUID
    created_at: datetime
    action: AccessAction
    outcome: str
    fields: list[AccessFieldDTO]
    by_self: bool
    by_administrator: bool
    actor_person_id: UUID | None
    actor_name: str | None
    request_id: UUID | None
    comment: str | None
    collective_name: str | None = None
