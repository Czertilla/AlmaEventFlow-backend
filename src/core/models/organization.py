from uuid import UUID
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin


class OrganizationAORM(Base, UUIDMixin):
    __tablename__ = "organization"
    __abstract__ = True

    type: Mapped[str] = mapped_column(String(16))


class OrganizationBaseORM(OrganizationAORM):
    __abstract__ = True

    name: Mapped[str] = mapped_column(String(128), index=True)


class OrganizationPrincipalORM(OrganizationBaseORM):
    __abstract__ = True

    principal_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("person.id", ondelete="SET NULL")
    )
