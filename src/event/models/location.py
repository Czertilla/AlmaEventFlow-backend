from sqlalchemy import Float
from sqlalchemy.orm import Mapped, mapped_column

from core.models.location import LocationAORM

from ._base import ModuleBase


class LocationORM(ModuleBase, LocationAORM):
    lat: Mapped[float | None] = mapped_column(Float, default=None)
    lon: Mapped[float | None] = mapped_column(Float, default=None)
    """Where it is on a map, as geo last told; ``None`` for a text-only location."""
