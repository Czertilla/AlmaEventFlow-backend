from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import BigSerialMixin
from geo.models.spot import OptionalSpotMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .region import RegionORM


class CityORM(ModuleBase, Base, BigSerialMixin, OptionalSpotMixin):
    __tablename__ = "city"

    region_id: Mapped[int] = mapped_column(
        ForeignKey("region.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(128))
    acronym: Mapped[str | None] = mapped_column(String(64))

    region: Mapped["RegionORM"] = relationship(back_populates="cities")
