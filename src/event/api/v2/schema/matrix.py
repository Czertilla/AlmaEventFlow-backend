import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.schema.v1.mixin.dto import FromDTOMixinV1
from event.api.v1.schema.role import RoleRead
from event.api.v2.schema.attendance import AttendanceReadV2
from event.api.v2.schema.event_page import RosterMember
from event.api.v2.schema.feed import EventPlace, decode_cursor, encode_cursor
from event.dto.feed import EventKeyDTO, FeedDirection
from event.dto.matrix import MatrixParamsDTO
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1

MAX_MATRIX_LIMIT = 50
MAX_RANGE_DAYS = 731


class MatrixParams(BaseModel):
    direction: FeedDirection = Field(
        default=FeedDirection.around,
        description=(
            "As in the feed: `around` a day, or the next events `past` / `future` "
            "of `cursor`. Ignored when both ends of a range are given."
        ),
    )
    anchor: datetime.date | None = Field(
        default=None, description="Today when omitted."
    )
    cursor: str | None = None
    limit: int = Field(
        default=20, ge=1, le=MAX_MATRIX_LIMIT, description="Events per side."
    )
    date_from: datetime.date | None = Field(
        default=None,
        description="With `date_to`: every event of the range, no paging.",
    )
    date_to: datetime.date | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.cursor is not None:
            decode_cursor(self.cursor)
        if (self.date_from is None) != (self.date_to is None):
            raise ValueError("date_from and date_to go together")
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from is after date_to")
            if (self.date_to - self.date_from).days > MAX_RANGE_DAYS:
                raise ValueError(
                    f"the range is longer than {MAX_RANGE_DAYS} days"
                )
        return self

    def to_dto(self) -> MatrixParamsDTO:
        return MatrixParamsDTO(
            direction=self.direction,
            anchor=self.anchor,
            cursor=decode_cursor(self.cursor) if self.cursor else None,
            limit=self.limit,
            date_from=self.date_from,
            date_to=self.date_to,
        )


class CollectiveEvent(FromDTOMixinV1, BaseModel):
    """An event the collective takes part in, with the collective's participation."""

    id: UUID
    name: str
    date: datetime.date | None
    status: EventStatusEnumV1
    level: EventLevelEnumV1 | None
    type: EventTypeEnumV1 | None
    format: EventFormatEnumV1
    location: EventPlace | None
    participation_id: UUID
    created_at: datetime.datetime
    edited_at: datetime.datetime | None

    model_config = ConfigDict(from_attributes=True)


class CollectiveEvents(FromDTOMixinV1, BaseModel):
    items: list[CollectiveEvent] = Field(
        description="The latest first, undated ones on top."
    )
    truncated: bool = Field(
        description="There are more events than the answer holds."
    )

    model_config = ConfigDict(from_attributes=True)


class CollectiveRoster(FromDTOMixinV1, BaseModel):
    members: list[RosterMember] = Field(
        description="By name, the former members too."
    )
    roles: list[RoleRead] = Field(description="By name.")

    model_config = ConfigDict(from_attributes=True)


class AttendanceMatrix(FromDTOMixinV1, BaseModel):
    """Who was declared for which event: `attendances` are the places of the
    participations of `events`. `members` and `roles` are the same in every window."""

    members: list[RosterMember]
    roles: list[RoleRead]
    events: list[CollectiveEvent] = Field(
        description="Oldest first, no templates."
    )
    attendances: list[AttendanceReadV2]
    has_more_past: bool
    has_more_future: bool
    past_cursor: str | None
    future_cursor: str | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("past_cursor", "future_cursor", mode="before")
    @classmethod
    def _encode(cls, value: Any) -> Any:
        return encode_cursor(value) if isinstance(value, EventKeyDTO) else value
