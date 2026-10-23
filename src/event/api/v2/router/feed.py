from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from event.api.v2.schema.feed import EventCard, EventFeed, FeedParams
from event.dependency.view import ViewUOWDep
from event.dto.member_profile import ProfileViewerDTO
from event.service.feed import FeedService

router = APIRouter(prefix="/feed", tags=["feed"])

MAX_CARD_IDS = 100


@router.get("", responses={**auth_responses()})
async def get_feed(
    user: UserJWTDep,
    uow: ViewUOWDep,
    params: Annotated[FeedParams, Query()],
) -> EventFeed:
    """Events around a day, or the next ones in either direction, each with the
    caller's own places and the counters of their collectives: what a list of
    events needs in one answer. Keyset paging, so a change of the list between two
    requests neither repeats nor skips an event."""
    viewer = ProfileViewerDTO(
        person_id=user.person_id, is_superuser=user.is_superuser
    )
    return EventFeed.from_dto(
        await FeedService(uow).feed(params.to_dto(), viewer)
    )


@router.get("/cards", responses={**auth_responses()})
async def get_cards(
    user: UserJWTDep,
    uow: ViewUOWDep,
    id: Annotated[list[UUID], Query(min_length=1, max_length=MAX_CARD_IDS)],
) -> list[EventCard]:
    """The same cards by id, in the order asked; an event that does not exist or
    that the caller may not see is left out."""
    viewer = ProfileViewerDTO(
        person_id=user.person_id, is_superuser=user.is_superuser
    )
    return [
        EventCard.from_dto(c) for c in await FeedService(uow).cards(id, viewer)
    ]


@router.get("/pending", responses={**auth_responses()})
async def get_pending(user: UserJWTDep, uow: ViewUOWDep) -> list[EventCard]:
    """Active events where a place of the caller is declared and nobody has marked
    it yet, the earliest first (at most 100)."""
    viewer = ProfileViewerDTO(
        person_id=user.person_id, is_superuser=user.is_superuser
    )
    return [
        EventCard.from_dto(c) for c in await FeedService(uow).pending(viewer)
    ]
