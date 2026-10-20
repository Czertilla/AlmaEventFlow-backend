from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OrganizationRefDTO:
    id: UUID
    name: str
    type: str
