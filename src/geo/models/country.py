from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import SmallSerialMixin
from geo.models.spot import OptionalSpotMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .region import RegionORM


class CountryORM(ModuleBase, Base, SmallSerialMixin, OptionalSpotMixin):
    __tablename__ = "country"

    name: Mapped[str] = mapped_column(String(128))
    code: Mapped[str | None] = mapped_column(String(16))

    regions: Mapped[list["RegionORM"]] = relationship(back_populates="country")
