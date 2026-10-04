from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OrganizationDTO:
    id: UUID
    name: str
    acronym: str | None
