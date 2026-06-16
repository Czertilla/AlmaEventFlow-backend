from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response, status

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from event.dependency.calendar import CalendarUOWDep
from event.models.calendar import CalendarSubscriptionORM
from event.schema.calendar import (
    AvailableFeeds,
    SubscriptionCreate,
    SubscriptionCreated,
    SubscriptionRead,
)
from event.service.calendar.feed import CalendarFeedService
from event.service.calendar.subscription import CalendarSubscriptionService

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _feed_url(request: Request, token: str) -> str:
    return str(request.url_for("get_calendar_feed", token=token, secure=True))


def _to_created(
    request: Request, sub: CalendarSubscriptionORM, token: str
) -> SubscriptionCreated:
    return SubscriptionCreated(
        id=sub.id,
        type=sub.type,
        title=sub.title,
        collective_id=sub.collective_id,
        is_active=sub.is_active,
        feed_url=_feed_url(request, token),
        created_at=sub.created_at,
        last_accessed_at=sub.last_accessed_at,
    )


@router.get("/available-feeds", responses={**auth_responses()})
async def get_available_feeds(
    user: UserJWTDep,
    uow: CalendarUOWDep,
) -> AvailableFeeds:
    return await CalendarSubscriptionService(uow).available_feeds(user)


@router.get("/subscriptions", responses={**auth_responses()})
async def list_subscriptions(
    user: UserJWTDep,
    uow: CalendarUOWDep,
) -> list[SubscriptionRead]:
    subs = await CalendarSubscriptionService(uow).list_active(user)
    return [SubscriptionRead.model_validate(sub) for sub in subs]


@router.post("/subscriptions", responses={**auth_responses()})
async def create_subscription(
    data: SubscriptionCreate,
    user: UserJWTDep,
    uow: CalendarUOWDep,
    request: Request,
) -> SubscriptionCreated:
    sub, token = await CalendarSubscriptionService(uow).create(user, data)
    return _to_created(request, sub, token)


@router.post(
    "/subscriptions/{subscription_id}/rotate-token",
    responses={**auth_responses()},
)
async def rotate_subscription_token(
    subscription_id: UUID,
    user: UserJWTDep,
    uow: CalendarUOWDep,
    request: Request,
) -> SubscriptionCreated:
    sub, token = await CalendarSubscriptionService(uow).rotate_token(
        user, subscription_id
    )
    return _to_created(request, sub, token)


@router.delete(
    "/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**auth_responses()},
)
async def delete_subscription(
    subscription_id: UUID,
    user: UserJWTDep,
    uow: CalendarUOWDep,
) -> None:
    await CalendarSubscriptionService(uow).delete(user, subscription_id)


@router.get("/feed/{token}.ics", name="get_calendar_feed")
async def get_calendar_feed(
    token: str,
    uow: CalendarUOWDep,
    if_none_match: str | None = Header(default=None),
) -> Response:
    """Public ICS feed — no Authorization header (external calendar clients
    subscribe by URL only). Security relies on the unguessable token."""
    result = await CalendarFeedService(uow).render(
        token, if_none_match=if_none_match
    )
    headers = {
        "ETag": result.etag,
        "Cache-Control": "private, max-age=300",
    }
    if result.not_modified:
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED, headers=headers
        )
    filename = quote(f"{result.calendar_name}.ics")
    headers["Content-Disposition"] = (
        f"inline; filename=\"calendar.ics\"; filename*=UTF-8''{filename}"
    )
    return Response(
        content=result.ics,
        media_type="text/calendar; charset=utf-8",
        headers=headers,
    )
