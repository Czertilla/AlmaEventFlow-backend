from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from event.enum.calendar import CalendarSubscriptionTypeEnum


class SubscriptionCreate(BaseModel):
    type: CalendarSubscriptionTypeEnum
    collective_id: UUID | None = None

    @model_validator(mode="after")
    def _check_collective(self) -> "SubscriptionCreate":
        needs_collective = self.type in (
            CalendarSubscriptionTypeEnum.personal_collective,
            CalendarSubscriptionTypeEnum.principal_collective,
        )
        if needs_collective and self.collective_id is None:
            raise ValueError(
                f"collective_id is required for type '{self.type.value}'"
            )
        if (
            self.type == CalendarSubscriptionTypeEnum.personal_all
            and self.collective_id is not None
        ):
            raise ValueError(
                "collective_id must be omitted for type 'personal_all'"
            )
        return self


class SubscriptionRead(BaseModel):
    id: UUID
    type: CalendarSubscriptionTypeEnum
    title: str
    collective_id: UUID | None
    is_active: bool
    # token cannot be recovered from its hash, so feed_url is only populated on
    # create / rotate-token responses; it is null when listing subscriptions.
    feed_url: str | None = None
    created_at: datetime
    last_accessed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreated(SubscriptionRead):
    """Returned by create / rotate-token — ``feed_url`` is always present."""

    feed_url: str


class FeedDescriptor(BaseModel):
    type: CalendarSubscriptionTypeEnum
    title: str
    collective_id: UUID | None = None


class AvailableFeeds(BaseModel):
    personal: FeedDescriptor | None = None
    member_collectives: list[FeedDescriptor] = []
    principal_collectives: list[FeedDescriptor] = []
