from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin


class PersonAORM(Base, UUIDMixin):
    __tablename__ = "person"
    __abstract__ = True


class PersonBaseORM(PersonAORM):
    __abstract__ = True

    surname: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(128))
    patronymic: Mapped[str | None] = mapped_column(String(128))