import datetime

from event.enum.calendar import CalendarSubscriptionTypeEnum
from event.models.calendar import (
    CalendarChangeLogORM,
    CalendarSubscriptionORM,
)
from event.uow.calendar import CalendarUOW
from .mapper import OWNER_ATTENDANCE, OWNER_PARTICIPATION
from .model import FeedItem

GRACE_DAYS = 90
PERSONAL_PAST_DAYS = 90
PRINCIPAL_PAST_DAYS = 180
FUTURE_DAYS = 365


class CalendarVisibilityResolver:
    """Resolves the set of visible events (and removed-event logs) for a feed.

    Must run inside an open ``CalendarUOW`` transaction.
    """

    def __init__(
        self, uow: CalendarUOW, now: datetime.datetime | None = None
    ) -> None:
        self.uow = uow
        self._now = now or datetime.datetime.now(datetime.timezone.utc)

    async def resolve(
        self, subscription: CalendarSubscriptionORM
    ) -> tuple[list[FeedItem], list[CalendarChangeLogORM]]:
        today = self._now.date()
        future = today + datetime.timedelta(days=FUTURE_DAYS)

        if subscription.type == CalendarSubscriptionTypeEnum.personal_all:
            past = today - datetime.timedelta(days=PERSONAL_PAST_DAYS)
            rows = await self.uow.calendar_feed.personal_all(
                subscription.person_id, past, future
            )
            return await self._build_items(rows, OWNER_ATTENDANCE), []

        if subscription.type == CalendarSubscriptionTypeEnum.personal_collective:
            past = today - datetime.timedelta(days=PERSONAL_PAST_DAYS)
            rows = await self.uow.calendar_feed.personal_collective(
                subscription.person_id,
                subscription.collective_id,
                past,
                future,
            )
            return await self._build_items(rows, OWNER_ATTENDANCE), []

        past = today - datetime.timedelta(days=PRINCIPAL_PAST_DAYS)
        grace_since = self._now - datetime.timedelta(days=GRACE_DAYS)
        rows = await self.uow.calendar_feed.principal_collective(
            subscription.collective_id, past, future, grace_since
        )
        logs = await self.uow.calendar_change_logs.get_for_collective_since(
            subscription.collective_id, grace_since
        )
        return await self._build_items(rows, OWNER_PARTICIPATION), logs

    async def _build_items(
        self, rows: list[tuple], owner_kind: str
    ) -> list[FeedItem]:
        if not rows:
            return []
        event_ids = [event.id for event, _ in rows]
        stages = await self.uow.calendar_feed.stages_for_events(event_ids)
        stages_by_event: dict = {}
        for stage in stages:
            stages_by_event.setdefault(stage.event_id, []).append(stage)
        return [
            FeedItem(
                event=event,
                owner_kind=owner_kind,
                owner_id=owner_id,
                stages=stages_by_event.get(event.id, []),
            )
            for event, owner_id in rows
        ]
