from uuid import UUID
from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin

from profile.models.person import PersonORM
from profile.enum.contact import ContactType
from ._base import ModuleBase


class ContactORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "contact"

    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE")
    )
    type: Mapped[ContactType] = mapped_column(
        Enum(ContactType, name="contact_type")
    )
    value: Mapped[str] = mapped_column(String(256))
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)

    person: Mapped["PersonORM"] = relationship(back_populates="contacts")
