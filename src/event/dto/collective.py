from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CollectiveSummaryDTO:
    id: UUID
    name: str
    principal_id: UUID
    is_verified: bool
