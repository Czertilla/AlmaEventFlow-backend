from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin


class AddressAORM(Base, UUIDMixin):
    __tablename__ = "address"
    __abstract__ = True

    name: Mapped[str] = mapped_column(String(512))
