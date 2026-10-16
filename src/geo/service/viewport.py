TILE_PX = 256
MAX_CLUSTER_ZOOM = 17
MAX_MERCATOR_LAT = 85.0511


def world_px(zoom: float) -> float:
    return TILE_PX * 2**zoom


def bbox_ranges(west: float, east: float) -> list[tuple[float, float]]:
    """West above east crosses the antimeridian (RFC 7946 §5.2)."""
    if west <= east:
        return [(west, east)]
    return [(west, 180.0), (-180.0, east)]
