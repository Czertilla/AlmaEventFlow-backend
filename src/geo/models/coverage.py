from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database.sqlalchemy.core import Base
from core.database.sqlalchemy.mixins.models import SerialMixin

from ._base import ModuleBase


class AddressCoverageCellORM(ModuleBase, Base, SerialMixin):
    __tablename__ = "address_coverage_cell"

    cell_row: Mapped[int]
    cell_col: Mapped[int]
    source: Mapped[str] = mapped_column(String(32), default="osm")
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    """Explicit ``timezone=True``: see ``AddressORM.synced_at``'s note on
    ``type_annotation_map`` not applying to a bare ``mapped_column()``."""

    __table_args__ = (
        Index(
            "uq_address_coverage_cell",
            "cell_row",
            "cell_col",
            "source",
            unique=True,
        ),
    )
