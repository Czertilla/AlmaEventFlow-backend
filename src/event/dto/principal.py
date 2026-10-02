from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CollectivePrincipalDTO:
    id: UUID
    principal_id: UUID
    is_verified: bool


@dataclass(frozen=True, slots=True)
class MemberIdentityDTO:
    id: UUID
    collective_id: UUID
    person_id: UUID
