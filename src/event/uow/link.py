from core.uow.sqlalchemy import UnitOfWork
from event.repository.link import EventLinkRepo


class LinkMixin:
    links: EventLinkRepo


class LinkUOW(UnitOfWork, LinkMixin): ...