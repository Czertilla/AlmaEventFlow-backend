from typing import TYPE_CHECKING
from sqlalchemy import UUID, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin


from user.models.oauth_account import OAuthAccountORM
from ._base import ModuleBase

if TYPE_CHECKING:
    from .person import PersonORM


class UserORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user"

    person_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("person.id"), unique=True
    )

    username: Mapped[str | None] = mapped_column(String(), unique=True)
    email: Mapped[str] = mapped_column(String(256))
    hashed_password: Mapped[bytes]
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    oauth_accounts: Mapped[list[OAuthAccountORM]] = relationship(
        "OAuthAccountORM", lazy="joined"
    )
    person: Mapped["PersonORM"] = relationship(back_populates="user")
