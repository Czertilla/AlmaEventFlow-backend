from uuid import UUID

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin


class UserORM(Base, UUIDMixin, TimestampMixin):
    """A bot account linked to an AlmaEventFlow identity. ``person_id`` is the
    cross-service join key shared with every other AEF service. The row can
    now exist ahead of any actual link — ``email``/``is_verified`` are kept in
    sync from ``user``-service's ``account.*`` events (see
    ``bot.service.account.AccountEventService``) as soon as a linkable person
    has an account at all, so the data is ready by the time ``/start`` runs."""

    __tablename__ = "user"

    person_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(256), default=None)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_client_id: Mapped[UUID | None] = mapped_column(default=None)
    """The notify ``client`` row id registered for this person's Telegram
    chat (``transport=telegram``), so unlinking can deregister it."""
