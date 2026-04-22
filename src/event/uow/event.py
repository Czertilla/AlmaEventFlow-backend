from core.uow.sqlalchemy import UnitOfWork
from event.repository.event import EventRepo, EventStatusRepo


class EventMixin:
    events: EventRepo

class EventStatusMixin:
    event_statuses: EventStatusRepo


class EventUOW(UnitOfWork, EventMixin): ...


class EventStatusUOW(UnitOfWork, EventStatusMixin): ...
