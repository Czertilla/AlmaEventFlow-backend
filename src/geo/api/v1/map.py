from logging import getLogger

from fastapi import APIRouter, Depends, Query

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses
from core.schema.pagination import SPageParam
from geo.dependency.address import AddressUOWDep
from geo.dependency.location import LocationUOWDep
from geo.schema.map import MapResult
from geo.service.address import AddressService
from geo.service.location import LocationService

router = APIRouter(prefix="/map", tags=["map"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_map(
    address_uow: AddressUOWDep,
    location_uow: LocationUOWDep,
    user: UserJWTDep,
    min_lat: float = Query(..., ge=-90, le=90),
    min_lon: float = Query(..., ge=-180, le=180),
    max_lat: float = Query(..., ge=-90, le=90),
    max_lon: float = Query(..., ge=-180, le=180),
    page_param=Depends(SPageParam),
) -> MapResult:
    """Both marker types (addresses and locations) inside a bounding box,
    for a map component to render -- backed by the GIST spatial index on
    ``spot`` via PostGIS's ``&&`` bbox operator, paginated independently."""
    addresses = await AddressService(address_uow).search_in_bbox(
        min_lat, min_lon, max_lat, max_lon, page_param
    )
    locations = await LocationService(location_uow).search_in_bbox(
        min_lat, min_lon, max_lat, max_lon, page_param
    )
    return MapResult(addresses=addresses, locations=locations)
