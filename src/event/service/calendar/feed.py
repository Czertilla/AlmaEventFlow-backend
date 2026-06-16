import datetime
import hashlib
from dataclasses import dataclass

from fastapi import status

from core.schema.error import ErrorCode
from core.service.base import BaseService
from core.utils.exc.http import VancedHTTPException
from event.uow.calendar import CalendarUOW
from .ics import CalendarIcsRenderer
from .mapper import CalendarEventMapper
from .token import CalendarTokenService
from .visibility import CalendarVisibilityResolver


@dataclass
class FeedResult:
    etag: str
    not_modified: bool
    calendar_name: str
    ics: str | None


class CalendarFeedService(BaseService[CalendarUOW]):
    def __init__(self, uow: CalendarUOW) -> None:
        super().__init__(uow)
        self._tokens = CalendarTokenService()
        self._renderer = CalendarIcsRenderer()

    async def render(
        self, token: str, *, if_none_match: str | None = None
    ) -> FeedResult:
        now = datetime.datetime.now(datetime.timezone.utc)
        token_hash = self._tokens.hash(token)
        async with self.uow as uow:
            subscription = (
                await self.uow.calendar_subscriptions.get_by_token_hash(
                    token_hash
                )
            )
            if subscription is None or not subscription.is_active:
                raise VancedHTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ErrorCode.CALENDAR_SUBSCRIPTION_NOT_FOUND,
                )

            resolver = CalendarVisibilityResolver(self.uow, now=now)
            items, logs = await resolver.resolve(subscription)

            mapper = CalendarEventMapper(now=now)
            vevents = mapper.map_items(items) + mapper.map_removed(logs)

            etag = self._etag(subscription.id, vevents)

            await self.uow.calendar_subscriptions.update_one(
                subscription.id, {"last_accessed_at": now}
            )
            await uow.commit()

            if if_none_match and self._matches(if_none_match, etag):
                return FeedResult(
                    etag=etag,
                    not_modified=True,
                    calendar_name=subscription.title,
                    ics=None,
                )

            ics = self._renderer.render(subscription.title, vevents)
            return FeedResult(
                etag=etag,
                not_modified=False,
                calendar_name=subscription.title,
                ics=ics,
            )

    @staticmethod
    def _etag(subscription_id, vevents) -> str:
        last_modified = max(
            (ve.last_modified for ve in vevents),
            default=datetime.datetime.min.replace(
                tzinfo=datetime.timezone.utc
            ),
        )
        raw = f"{subscription_id}:{len(vevents)}:{last_modified.isoformat()}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
        return f'"{digest}"'

    @staticmethod
    def _matches(if_none_match: str, etag: str) -> bool:
        candidates = [c.strip() for c in if_none_match.split(",")]
        return etag in candidates or "*" in candidates
