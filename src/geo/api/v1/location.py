from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from core.schema.pagination import SPage, SPageParam
from geo.dependency.location import LocationUOWDep
from geo.filter.location import LocationFilter
from geo.schema.location import (
    LocationCreate,
    LocationPatch,
    LocationPatchData,
    LocationPut,
    LocationPutData,
    LocationRead,
)
from geo.service.location import LocationService

router = APIRouter(prefix="/locations", tags=["location"])

logger = getLogger(__name__)

@router.get("", responses={**auth_responses()})
async def get_locations(
    uow: LocationUOWDep,
    user: UserJWTDep,
    filter: LocationFilter = FilterDepends(LocationFilter),
    page_param=Depends(SPageParam),
) -> SPage[LocationRead]:
    return await LocationService(uow).search(filter, page_param)

@router.get("/{location_id}", responses={**auth_responses(), **entity_not_found_responses("location")})
async def get_location(
    location_id: UUID, user: UserJWTDep, uow: LocationUOWDep
) -> LocationRead:
    return await LocationService(uow).read(location_id)

@router.post("", responses={**auth_responses()})
async def create_location(
    location: LocationCreate,
    user: SuperUserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    return await LocationService(uow).create(location)

@router.put("/{location_id}", responses={**auth_responses(), **entity_not_found_responses("location")})
async def put_location(
    location_id: UUID,
    location: LocationPutData,
    user: SuperUserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    return await LocationService(uow).put(
        LocationPut(id=location_id, **location.model_dump())
    )

@router.patch("/{location_id}", responses={**auth_responses(), **entity_not_found_responses("location")})
async def patch_location(
    location_id: UUID,
    location: LocationPatchData,
    user: SuperUserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    return await LocationService(uow).patch(
        LocationPatch(id=location_id, **location.model_dump())
    )

@router.delete("/{location_id}", responses={**auth_responses(), **entity_not_found_responses("location")})
async def delete_location(
    location_id: UUID, user: SuperUserJWTDep, uow: LocationUOWDep
) -> None:
    await LocationService(uow).delete(location_id)