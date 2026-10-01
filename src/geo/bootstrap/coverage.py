"""Fixed geographic grid for tracking which areas have already been fetched
from an external address source -- independent of any one bootstrap run's
own ``--grid`` (which slices a single city's bbox into N pieces and isn't
globally addressable). A cell here is a stateless function of (lat, lon)
alone, so "is this point covered" needs no city context.
"""

from collections.abc import Iterator

from geo.bootstrap.sources import BBox

CELL_SIZE_DEG = 0.05
"""~5.5km latitude / ~3.2km longitude at Moscow's latitude -- coarse enough
that a live fetch's Overpass query stays small, fine enough that "covered"
doesn't falsely span into clearly-unrelated areas."""


def cell_of(lat: float, lon: float) -> tuple[int, int]:
    return (int(lat // CELL_SIZE_DEG), int(lon // CELL_SIZE_DEG))


def bbox_of_cell(row: int, col: int) -> BBox:
    min_lat, min_lon = row * CELL_SIZE_DEG, col * CELL_SIZE_DEG
    return (min_lat, min_lon, min_lat + CELL_SIZE_DEG, min_lon + CELL_SIZE_DEG)


def cells_covering_bbox(bbox: BBox) -> Iterator[tuple[int, int]]:
    min_lat, min_lon, max_lat, max_lon = bbox
    min_row, max_row = cell_of(min_lat, min_lon)[0], cell_of(max_lat, max_lon)[0]
    min_col, max_col = cell_of(min_lat, min_lon)[1], cell_of(max_lat, max_lon)[1]
    for row in range(min_row, max_row + 1):
        for col in range(min_col, max_col + 1):
            yield (row, col)
