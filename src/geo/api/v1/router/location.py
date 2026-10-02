from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.v1.pagination import PageParamV1, PageV1
from geo.api.v1.schema.location import (
    LocationCreate,
    LocationFromAddressCreate,
    LocationPatch,
    LocationPatchData,
    LocationPut,
    LocationPutData,
    LocationRead,
)
from geo.api.v1.schema.point import Point
from geo.dependency.location import LocationUOWDep
from geo.filter.location import LocationFilter
from geo.service.location import LocationService

router = APIRouter(prefix="/locations", tags=["location"])

logger = getLogger(__name__)


@router.get("", responses={**auth_responses()})
async def get_locations(
    uow: LocationUOWDep,
    user: UserJWTDep,
    filter: LocationFilter = FilterDepends(LocationFilter),
    page_param: PageParamV1 = Depends(PageParamV1),
    near_lat: float | None = None,
    near_lon: float | None = None,
) -> PageV1[LocationRead]:
    # near_lat/near_lon sort by distance instead of name, but only when search is empty (see service)
    near = (
        Point(lat=near_lat, lon=near_lon).to_dto()
        if near_lat is not None and near_lon is not None
        else None
    )
    return PageV1[LocationRead].from_dto(
        await LocationService(uow).search(
            filter.to_dto(), page_param.to_dto(), near=near
        )
    )


@router.get(
    "/{location_id}",
    responses={**auth_responses(), **entity_not_found_responses("location")},
)
async def get_location(
    location_id: UUID, user: UserJWTDep, uow: LocationUOWDep
) -> LocationRead:
    return LocationRead.from_dto(await LocationService(uow).read(location_id))


@router.post("", responses={**auth_responses()})
async def create_location(
    location: LocationCreate,
    user: UserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    """Any authenticated user may add a location -- e.g. a collective
    principal picking/pinning a venue for an event. Editing/removing an
    existing location stays superuser-only (no ownership model exists yet
    to gate that safely per-collective)."""
    return LocationRead.from_dto(await LocationService(uow).create(location.to_dto()))


@router.post("/from-address", responses={**auth_responses()})
async def create_location_from_address(
    data: LocationFromAddressCreate,
    user: UserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    """Backend half of the "pick an address, optionally name it" flow: an
    address is already selected (via address search), this turns it into a
    location id usable for ``EventCreate.location_id``. Omitting ``name``
    reuses the existing address-proxy location instead of creating a
    duplicate."""
    return LocationRead.from_dto(
        await LocationService(uow).create_from_address(data.address_id, data.name)
    )


@router.put(
    "/{location_id}",
    responses={**auth_responses(), **entity_not_found_responses("location")},
)
async def put_location(
    location_id: UUID,
    location: LocationPutData,
    user: SuperUserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    return LocationRead.from_dto(
        await LocationService(uow).put(
            LocationPut.model_validate(
                {"id": location_id, **location.model_dump()}
            ).to_dto()
        )
    )


@router.patch(
    "/{location_id}",
    responses={**auth_responses(), **entity_not_found_responses("location")},
)
async def patch_location(
    location_id: UUID,
    location: LocationPatchData,
    user: SuperUserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    return LocationRead.from_dto(
        await LocationService(uow).patch(
            LocationPatch.model_validate(
                {"id": location_id, **location.model_dump()}
            ).to_dto()
        )
    )


@router.delete(
    "/{location_id}",
    responses={**auth_responses(), **entity_not_found_responses("location")},
)
async def delete_location(
    location_id: UUID, user: SuperUserJWTDep, uow: LocationUOWDep
) -> None:
    await LocationService(uow).delete(location_id)
