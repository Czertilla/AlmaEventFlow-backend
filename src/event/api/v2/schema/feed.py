import base64
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
from event.api.v1.schema.role import RolePreview
from event.api.v2.schema.attendance import AttendanceReadV2
from event.dto.feed import (
    EventFilterViewDTO,
    EventKeyDTO,
    FeedDirection,
    FeedParamsDTO,
)
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1

MAX_FEED_LIMIT = 50
MAX_FILTER_IDS = 50


def encode_cursor(key: EventKeyDTO) -> str:
    raw = f"{key.date.isoformat()}|{key.id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> EventKeyDTO:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        day, event_id = base64.urlsafe_b64decode(padded).decode().split("|")
        return EventKeyDTO(
            date=datetime.date.fromisoformat(day), id=UUID(event_id)
        )
    except ValueError as exc:
        raise ValueError("the cursor is not one this API gave") from exc


class FeedParams(BaseModel):
    direction: FeedDirection = Field(
        default=FeedDirection.around,
        description=(
            "`around`: the events before `anchor` and from it on, `limit` of each "
            "side. "
            "`past` / `future`: the next `limit` events before / after `cursor` "
            "(or before / from `anchor` when there is no cursor)."
        ),
    )
    anchor: datetime.date | None = Field(
        default=None,
        description="A day of the caller's calendar; today when omitted.",
    )
    cursor: str | None = Field(
        default=None,
        description="`past_cursor` / `future_cursor` of the previous answer, as given.",
    )
    limit: int = Field(
        default=10, ge=1, le=MAX_FEED_LIMIT, description="Events per side."
    )
    collective_id: list[UUID] = Field(
        default_factory=list,
        max_length=MAX_FILTER_IDS,
        description=(
            "Only the events these collectives take part in; every event when empty."
        ),
    )
    status: list[EventStatusEnumV1] = Field(
        default_factory=list,
        description=(
            "Any of the given statuses; all but `template` when empty. Only the "
            "leaders "
            "of the collectives taking part see a status other than `active`."
        ),
    )
    type: list[EventTypeEnumV1] = Field(default_factory=list)
    level: list[EventLevelEnumV1] = Field(default_factory=list)
    format: list[EventFormatEnumV1] = Field(default_factory=list)
    date_from: datetime.date | None = Field(
        default=None, description="Only the events on this day or later."
    )

    @model_validator(mode="after")
    def _check_position(self) -> Self:
        if self.cursor is not None:
            decode_cursor(self.cursor)
        return self

    def to_dto(self) -> FeedParamsDTO:
        return FeedParamsDTO(
            direction=self.direction,
            anchor=self.anchor,
            cursor=decode_cursor(self.cursor) if self.cursor else None,
            limit=self.limit,
            filters=EventFilterViewDTO(
                statuses=self.status,
                types=self.type,
                levels=self.level,
                formats=self.format,
                collective_ids=self.collective_id,
                date_from=self.date_from,
            ),
        )


class EventPlace(FromDTOMixinV1, BaseModel):
    """Where an event is, as geo last told: the text to show and a point on the map."""

    id: UUID
    name: str | None
    lat: float | None
    lon: float | None

    model_config = ConfigDict(from_attributes=True)


class EventCardParticipation(FromDTOMixinV1, BaseModel):
    id: UUID
    collective_id: UUID
    collective_name: str
    attended_count: int = Field(
        description="Places of the participation marked as attended."
    )
    total_count: int = Field(
        description="Places declared for the participation."
    )
    my_attendance: AttendanceReadV2 | None = Field(
        description="The caller's own place, when they are a member of the collective."
    )

    model_config = ConfigDict(from_attributes=True)


class EventCard(FromDTOMixinV1, BaseModel):
    """An event as a list shows it. Only the collectives of the caller take part
    in `participations`; `edited_at ?? created_at` tells which copy is newer."""

    id: UUID
    name: str
    date: datetime.date | None
    status: EventStatusEnumV1
    level: EventLevelEnumV1 | None
    type: EventTypeEnumV1 | None
    format: EventFormatEnumV1
    location: EventPlace | None
    starts_at: datetime.datetime | None = Field(
        description="The first stage start, if the event has stages."
    )
    ends_at: datetime.datetime | None = Field(
        description="The last stage end (its start when open-ended)."
    )
    participations: list[EventCardParticipation]
    created_at: datetime.datetime
    edited_at: datetime.datetime | None
    updated_at: datetime.datetime = Field(
        description=(
            "When the event or a place of its participations last changed: of two "
            "copies of a card the greater one is the newer. A deleted place leaves "
            "no trace in it."
        )
    )

    model_config = ConfigDict(from_attributes=True)


class EventFeed(FromDTOMixinV1, BaseModel):
    """Events in date order. `has_more_*` and the cursors speak of the sides that
    were asked for; the other side of a `past` or `future` request is `false`/`null`."""

    items: list[EventCard]
    has_more_past: bool
    has_more_future: bool
    past_cursor: str | None = Field(
        description="Of the earliest event returned."
    )
    future_cursor: str | None = Field(
        description="Of the latest event returned."
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("past_cursor", "future_cursor", mode="before")
    @classmethod
    def _encode(cls, value: Any) -> Any:
        return encode_cursor(value) if isinstance(value, EventKeyDTO) else value


class ViewerCollective(FromDTOMixinV1, BaseModel):
    id: UUID
    name: str
    is_verified: bool
    is_principal: bool = Field(description="The caller leads the collective.")
    member_id: UUID | None = Field(
        description="The caller's membership, if any."
    )
    member_is_active: bool | None
    roles: list[RolePreview] = Field(
        description="The roles of the caller's membership."
    )

    model_config = ConfigDict(from_attributes=True)


class ViewerContext(FromDTOMixinV1, BaseModel):
    """Who the caller is for the events: the collectives they lead or belong to."""

    person_id: UUID | None
    collectives: list[ViewerCollective]

    model_config = ConfigDict(from_attributes=True)
