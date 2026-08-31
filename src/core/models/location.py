from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin


class LocationAORM(Base, UUIDMixin):
    __tablename__ = "location"
    __abstract__ = True

    name: Mapped[str | None] = mapped_column(String(512), default=None)
    """Nullable: a location that's just an address with nothing more
    specific to say (an "address-proxy" location) has no name of its own."""
