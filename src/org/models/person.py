from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship

from core.models.person import PersonAORM
from ._base import ModuleBase

if TYPE_CHECKING:
    from .organization import OrganizationORM


class PersonORM(ModuleBase, PersonAORM):
    principal_of: Mapped[list["OrganizationORM"]] = relationship(
        back_populates="principal"
    )
