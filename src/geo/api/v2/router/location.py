from uuid import UUID

from fastapi import APIRouter

from core.dependencies.auth import UserJWTDep
from core.schema.error import auth_responses, entity_not_found_responses
from geo.api.v2.schema.location import LocationReadV2
from geo.dependency.location import LocationUOWDep
from geo.service.location import LocationService

router = APIRouter(prefix="/locations", tags=["location"])


@router.get(
    "/{location_id}",
    responses={**auth_responses(), **entity_not_found_responses("location")},
)
async def get_location(
    location_id: UUID, user: UserJWTDep, uow: LocationUOWDep
) -> LocationReadV2:
    return LocationReadV2.from_dto(await LocationService(uow).read(location_id))
