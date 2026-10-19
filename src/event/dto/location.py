import datetime
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RecentLocationDTO:
    location_id: UUID
    used_at: datetime.datetime
