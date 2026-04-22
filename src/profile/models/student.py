from typing import TYPE_CHECKING
from sqlalchemy import UUID, ForeignKey, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import (
    BigSerialMixin,
    SmallSerialMixin,
)

from profile.models.profile import ProfileORM
from ._base import ModuleBase

if TYPE_CHECKING:
    from .organization import OrganizationORM


class StudentDegree(ModuleBase, Base, SmallSerialMixin):
    __tablename__ = "student_degree"

    name: Mapped[str] = mapped_column(String(32))


class StudentGroupORM(ModuleBase, Base, BigSerialMixin):
    __tablename__ = "student_group"

    name: Mapped[str] = mapped_column(String(32), index=True)
    degree_id: Mapped[int] = mapped_column(ForeignKey("student_degree.id"))
    faculty_id: Mapped[UUID] = mapped_column(ForeignKey("organization.id"))
    grade: Mapped[int] = mapped_column(SmallInteger)

    degree: Mapped["StudentDegree"] = relationship(foreign_keys=[degree_id])
    faculty: Mapped["OrganizationORM"] = relationship(foreign_keys=[faculty_id])
    students: Mapped[list["StudentORM"]] = relationship(back_populates="group")


class StudentORM(ProfileORM):
    __tablename__ = "student"

    id: Mapped[UUID] = mapped_column(ForeignKey("profile.id"), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    faculty_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organization.id", ondelete="SET NULL"), default=None
    )
    group_id: Mapped[int] = mapped_column(ForeignKey("student_group.id"))
    is_budget: Mapped[bool | None]
    is_full: Mapped[bool | None]
    is_active: Mapped[bool] = mapped_column(default=True)

    group: Mapped["StudentGroupORM"] = relationship(back_populates="students")
    profile: Mapped["ProfileORM"] = relationship(foreign_keys=[id])
