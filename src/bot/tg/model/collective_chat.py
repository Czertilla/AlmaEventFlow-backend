from uuid import UUID

from sqlalchemy import BigInteger, String, UniqueConstraint, false, true
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin


class CollectiveChatORM(Base, UUIDMixin, TimestampMixin):
    """Maps a collective (event-service's own database — no FK, cross-service
    like ``calendar_subscription.owner_user_id``) to its official Telegram
    group chat. Set up by a collective principal via the bot's
    ``/setup_chat`` command, run inside the target chat while the bot has
    admin rights there."""

    __tablename__ = "collective_chat"
    __table_args__ = (
        UniqueConstraint("chat_id", name="uq_collective_chat_chat_id"),
        {"schema": "tg"},
    )

    collective_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    thread_id: Mapped[int | None] = mapped_column(default=None)
    """Optional forum-topic id, so a collective's announcements can live in
    their own thread instead of the chat's general stream."""
    set_by_id: Mapped[int] = mapped_column(BigInteger)
    announce_enabled: Mapped[bool] = mapped_column(
        default=True, server_default=true()
    )
    silent: Mapped[bool] = mapped_column(default=False, server_default=false())
    pin_announcements: Mapped[bool] = mapped_column(
        default=False, server_default=false()
    )
    language: Mapped[str | None] = mapped_column(String(8), default=None)
    """Language of the announcements posted to the chat; ``None`` means the
    bot's default language."""
