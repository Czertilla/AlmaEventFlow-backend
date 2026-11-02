from datetime import datetime
from profile.enum.access import AccessAction
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import UUIDMixin

from ._base import ModuleBase

ACTIONS = tuple(action.value for action in AccessAction)
VIAS = ("self", "superuser", "grant", "none")


class SensitiveAccessLogORM(ModuleBase, Base, UUIDMixin):
    __tablename__ = "sensitive_access_log"
    __table_args__ = (
        CheckConstraint(
            "action IN (" + ", ".join(f"'{action}'" for action in ACTIONS) + ")",
            name="ck_sensitive_access_log_action",
        ),
        CheckConstraint(
            "via IN (" + ", ".join(f"'{via}'" for via in VIAS) + ")",
            name="ck_sensitive_access_log_via",
        ),
        Index(
            "ix_sensitive_access_log_subject_created", "subject_person_id", "created_at"
        ),
        Index(
            "ix_sensitive_access_log_actor_created", "actor_person_id", "created_at"
        ),
        Index("ix_sensitive_access_log_request", "request_id"),
    )

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    actor_user_id: Mapped[UUID | None]
    actor_person_id: Mapped[UUID | None]
    subject_person_id: Mapped[UUID]
    request_id: Mapped[UUID | None]
    grant_id: Mapped[UUID | None]
    action: Mapped[str] = mapped_column(String(32))
    via: Mapped[str] = mapped_column(String(16))
    fields: Mapped[list[str]] = mapped_column(ARRAY(String(64)))
    outcome: Mapped[str] = mapped_column(String(64))
    notified: Mapped[bool] = mapped_column(default=False)
    request_id_http: Mapped[str | None] = mapped_column(String(64))
