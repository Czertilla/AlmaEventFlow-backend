from uuid import UUID
from fastapi import APIRouter
from logging import getLogger

from core.dependencies.auth import SuperUserJWTDep, UserJWTDep
from geo.dependency.location import LocationUOWDep
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

@router.get("/{location_id}")
async def get_location(
    location_id: UUID, user: UserJWTDep, uow: LocationUOWDep
) -> LocationRead:
    return await LocationService(uow).read(location_id)

@router.post("/new")
async def create_location(
    location: LocationCreate,
    user: SuperUserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    return await LocationService(uow).create(location)

@router.put("/{location_id}")
async def put_location(
    location_id: UUID,
    location: LocationPutData,
    user: SuperUserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    return await LocationService(uow).put(
        LocationPut(id=location_id, **location.model_dump())
    )

@router.patch("/{location_id}")
async def patch_location(
    location_id: UUID,
    location: LocationPatchData,
    user: SuperUserJWTDep,
    uow: LocationUOWDep,
) -> LocationRead:
    return await LocationService(uow).patch(
        LocationPatch(id=location_id, **location.model_dump())
    )

@router.delete("/{location_id}")
async def delete_location(
    location_id: UUID, user: SuperUserJWTDep, uow: LocationUOWDep
) -> None:
    await LocationService(uow).delete(location_id)