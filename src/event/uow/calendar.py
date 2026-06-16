from core.uow.sqlalchemy import UnitOfWork
from event.repository.calendar import (
    CalendarChangeLogRepo,
    CalendarFeedRepo,
    CalendarSubscriptionRepo,
)
from event.uow.collective import CollectiveMixin
from event.uow.member import MemberMixin


class CalendarSubscriptionMixin:
    calendar_subscriptions: CalendarSubscriptionRepo


class CalendarChangeLogMixin:
    calendar_change_logs: CalendarChangeLogRepo


class CalendarFeedMixin:
    calendar_feed: CalendarFeedRepo


class CalendarUOW(
    UnitOfWork,
    CalendarSubscriptionMixin,
    CalendarChangeLogMixin,
    CalendarFeedMixin,
    CollectiveMixin,
    MemberMixin,
):
    pass
