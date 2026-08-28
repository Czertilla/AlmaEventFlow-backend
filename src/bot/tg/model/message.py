from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin


class TelegramMessageORM(Base, UUIDMixin, TimestampMixin):
    """Correlates a domain id (``correlation_key``, e.g. a domain event id)
    with the Telegram message the bot already sent about it in a given chat,
    so a later update edits that message (+ a reply ping) instead of sending
    a new one. One row per (correlation_key, chat_id) — the same event can
    have separate messages in separate chats (a user's DM, a collective's
    group chat)."""

    __tablename__ = "message"
    __table_args__ = (
        UniqueConstraint(
            "correlation_key", "chat_id", name="uq_message_correlation_chat"
        ),
        {"schema": "tg"},
    )

    correlation_key: Mapped[str] = mapped_column(String(64), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)
