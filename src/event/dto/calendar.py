from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from event.enum.calendar import CalendarSubscriptionTypeEnum


@dataclass(frozen=True, slots=True)
class SubscriptionCreateDTO:
    type: CalendarSubscriptionTypeEnum
    collective_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class CalendarSubscriptionDTO:
    id: UUID
    type: CalendarSubscriptionTypeEnum
    title: str
    collective_id: UUID | None
    is_active: bool
    created_at: datetime
    last_accessed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FeedDescriptorDTO:
    type: CalendarSubscriptionTypeEnum
    title: str
    collective_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AvailableFeedsDTO:
    personal: FeedDescriptorDTO | None = None
    member_collectives: list[FeedDescriptorDTO] = field(default_factory=list)
    principal_collectives: list[FeedDescriptorDTO] = field(
        default_factory=list
    )
