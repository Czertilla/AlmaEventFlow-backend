from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from geo.api.v1.schema.point import Point
from geo.api.v2.schema.search import SearchResponse
from geo.dependency.address import AddressUOWDep
from geo.dto.search import SearchKind, SearchQueryDTO
from geo.service.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", responses={**auth_responses()})
async def search(
    uow: AddressUOWDep,
    user: UserJWTDep,
    q: Annotated[
        str | None,
        Query(max_length=200, description="Free text: street, house, place, city."),
    ] = None,
    lat: Annotated[
        float | None,
        Query(ge=-90, le=90, description="Latitude of the map centre or the user."),
    ] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    kinds: Annotated[
        list[Literal["address", "location"]] | None,
        Query(description="What to search; both by default."),
    ] = None,
    city_id: int | None = None,
    named_locations_only: Annotated[
        bool,
        Query(
            description=(
                "Skip the unnamed locations that only stand for an address "
                "(the address itself is already a result)."
            )
        ),
    ] = True,
    external: Annotated[
        Literal["auto", "off"],
        Query(
            description=(
                "`auto` asks the external geocoder when the local answer is "
                "short; `off` never does."
            )
        ),
    ] = "auto",
) -> SearchResponse:
    """Typeahead over addresses and named locations, ranked together.

    The city counts: "тверская москва" narrows to Moscow. With a point the
    nearer of equal matches comes first; with a point and no text the
    nearest places are listed, the houses around the point included when too
    few are stored. A text that names a settlement ("суздаль") lists the
    addresses nearest to its centre and says where it is in `place`.
    Addresses the external geocoder finds are stored, so every result has an
    id usable as `address_id`.
    """
    if (lat is None) != (lon is None):
        raise HTTPException(422, detail="lat and lon go together")
    near = (
        Point(lat=lat, lon=lon).to_dto()
        if lat is not None and lon is not None
        else None
    )
    if not (q and q.strip()) and near is None:
        raise HTTPException(422, detail="give q, or lat and lon")
    chosen: tuple[SearchKind, ...] = tuple(kinds) if kinds else ("location", "address")
    return SearchResponse.from_dto(
        await SearchService(uow).search(
            SearchQueryDTO(
                query=q,
                near=near,
                limit=limit,
                kinds=chosen,
                city_id=city_id,
                named_locations_only=named_locations_only,
                external=external == "auto",
            )
        )
    )
