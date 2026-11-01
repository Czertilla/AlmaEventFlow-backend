from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column

from core.models.organization import OrganizationAORM

from ._base import ModuleBase


class OrganizationORM(ModuleBase, OrganizationAORM):
    principal_id: Mapped[UUID | None] = mapped_column(index=True)
