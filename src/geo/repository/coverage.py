from sqlalchemy import exists, select

from core.database.sqlalchemy.core import SQLAlchemyRepository
from core.database.sqlalchemy.mixins.repositories import (
    IDRepositoryMixin,
    UpsertRepositoryMixin,
)
from geo.models.coverage import AddressCoverageCellORM as Model


class CoverageRepo(
    SQLAlchemyRepository[Model],
    IDRepositoryMixin[Model, int],
    UpsertRepositoryMixin[Model, int],
):
    model = Model
    conflict_index_elements = ["cell_row", "cell_col", "source"]

    async def covered(self, row: int, col: int, source: str = "osm") -> bool:
        stmt = select(
            exists().where(
                self.model.cell_row == row,
                self.model.cell_col == col,
                self.model.source == source,
            )
        )
        return bool((await self.execute(stmt)).scalar())
