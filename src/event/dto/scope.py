from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CollectiveScopeDTO:
    """The collectives a caller may read people of; `None` means no limit."""

    collective_ids: frozenset[UUID] | None = None

    def allows(self, collective_id: UUID) -> bool:
        return self.collective_ids is None or collective_id in self.collective_ids
