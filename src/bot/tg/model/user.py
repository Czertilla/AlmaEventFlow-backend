from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.model.user import UserORM
from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin


class TGUserORM(Base, TimestampMixin):
    __tablename__ = "user"
    __table_args__ = {"schema": "tg"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        unique=True,
        default=None,
    )
    is_bot: Mapped[bool] = mapped_column(default=False)
    first_name: Mapped[str] = mapped_column(String(length=64))
    last_name: Mapped[str | None] = mapped_column(
        String(length=64), default=None
    )
    username: Mapped[str | None] = mapped_column(
        String(length=32), default=None
    )
    language_code: Mapped[str | None] = mapped_column(
        String(length=8), default=None
    )
    is_premium: Mapped[bool | None] = mapped_column(default=None)

    is_superuser: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    user: Mapped[UserORM | None] = relationship(
        backref="bot_users", lazy="joined"
    )
