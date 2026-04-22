from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import SerialMixin
from geo.models.spot import OptionalSpotMixin
from ._base import ModuleBase

if TYPE_CHECKING:
    from .country import CountryORM
    from .city import CityORM


class RegionORM(ModuleBase, Base, SerialMixin, OptionalSpotMixin):
    __tablename__ = "region"

    country_id: Mapped[int] = mapped_column(
        ForeignKey("country.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(128))
    code: Mapped[str | None] = mapped_column(String(16))

    country: Mapped["CountryORM"] = relationship(back_populates="regions")
    cities: Mapped[list["CityORM"]] = relationship(back_populates="region")
