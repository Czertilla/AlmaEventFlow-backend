from datetime import datetime
from profile.enum.access import GrantStatus
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import TimestampMixin, UUIDMixin

from ._base import ModuleBase

GRANT_STATUSES = tuple(status.value for status in GrantStatus)


class AccessRequestORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    __tablename__ = "access_request"
    __table_args__ = (Index("ix_access_request_grantee", "grantee_person_id"),)

    grantee_person_id: Mapped[UUID]
    collective_id: Mapped[UUID]
    collective_name: Mapped[str] = mapped_column(String(128))
    comment: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime]
    created_by_user_id: Mapped[UUID]

    fields: Mapped[list["AccessRequestFieldORM"]] = relationship(
        order_by="AccessRequestFieldORM.field_key"
    )
    grants: Mapped[list["AccessGrantORM"]] = relationship(
        back_populates="request", order_by="AccessGrantORM.created_at"
    )


class AccessRequestFieldORM(ModuleBase, Base):
    __tablename__ = "access_request_field"

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("access_request.id", ondelete="CASCADE"), primary_key=True
    )
    field_key: Mapped[str] = mapped_column(String(64), primary_key=True)


class AccessGrantORM(ModuleBase, Base, UUIDMixin, TimestampMixin):
    __tablename__ = "access_grant"
    __table_args__ = (
        UniqueConstraint(
            "request_id", "subject_person_id", name="uq_access_grant_request_subject"
        ),
        CheckConstraint(
            "status IN (" + ", ".join(f"'{s}'" for s in GRANT_STATUSES) + ")",
            name="ck_access_grant_status",
        ),
        Index("ix_access_grant_subject_status", "subject_person_id", "status"),
    )

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("access_request.id", ondelete="CASCADE")
    )
    subject_person_id: Mapped[UUID] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(16), default=GrantStatus.PENDING.value)
    decided_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]
    consent_evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    request: Mapped[AccessRequestORM] = relationship(back_populates="grants")
