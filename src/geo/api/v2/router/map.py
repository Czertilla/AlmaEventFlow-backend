from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from geo.api.v2.schema.map import MapResponse
from geo.dependency.map import MapUOWDep
from geo.dto.map import MapQueryDTO
from geo.dto.search import SearchKind
from geo.service.map import MapService

router = APIRouter(prefix="/map", tags=["map"])


class GeoJSONResponse(JSONResponse):
    media_type = "application/geo+json"


def _parse_bbox(bbox: str) -> tuple[float, float, float, float]:
    try:
        west, south, east, north = (float(part) for part in bbox.split(","))
    except ValueError:
        raise HTTPException(
            422, detail="bbox is four numbers: west,south,east,north"
        ) from None
    if not (-180 <= west <= 180 and -180 <= east <= 180):
        raise HTTPException(422, detail="bbox longitudes are within -180..180")
    if not (-90 <= south <= north <= 90):
        raise HTTPException(
            422, detail="bbox latitudes are within -90..90, south not above north"
        )
    return west, south, east, north


@router.get("", response_class=GeoJSONResponse, responses={**auth_responses()})
async def get_map(
    uow: MapUOWDep,
    user: UserJWTDep,
    bbox: Annotated[
        str,
        Query(
            description=(
                "west,south,east,north in degrees (RFC 7946 order). West "
                "greater than east means a window across the antimeridian."
            ),
            examples=["37.3,55.5,37.9,55.9"],
        ),
    ],
    zoom: Annotated[
        float,
        Query(ge=0, le=22, description="The map's zoom level, fractions allowed."),
    ],
    radius_px: Annotated[
        int,
        Query(
            ge=24,
            le=256,
            description="Screen pixels one marker (or cluster) takes.",
        ),
    ] = 64,
    kinds: Annotated[
        list[Literal["address", "location"]] | None,
        Query(description="What to draw; both by default."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
) -> MapResponse:
    """Places in a map window, clustered for the zoom.

    The window is cut into cells of `radius_px` screen pixels (Web Mercator,
    so a cell is the same size on screen everywhere) and every cell becomes
    one feature: the place itself when it is alone, a cluster otherwise.
    The answer is bounded by the cells that fit the window, not by how
    dense the data is, so a crowded district cannot push the rest out.
    From zoom 17 on nothing is clustered.
    """
    west, south, east, north = _parse_bbox(bbox)
    chosen: tuple[SearchKind, ...] = tuple(kinds) if kinds else ("address", "location")
    return MapResponse.from_dto(
        await MapService(uow).view(
            MapQueryDTO(
                west=west,
                south=south,
                east=east,
                north=north,
                zoom=zoom,
                radius_px=radius_px,
                kinds=chosen,
                limit=limit,
            )
        )
    )
